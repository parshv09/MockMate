import logging
import os
import random
import tempfile
import time
import uuid
from datetime import timedelta
from typing import Callable, Optional, Tuple, TypeVar

from django.conf import settings
from django.db import OperationalError, transaction
from django.db.models import Q
from django.utils import timezone

from ..models import Answer, InterviewSession
from ..nlp_utils import analyze_transcript
from ..speech_utils import transcribe_audio
from .video_service import finalize_session_video_metrics

logger = logging.getLogger(__name__)

T = TypeVar("T")

DEFAULT_ANSWER_CLAIM_TIMEOUT_SECONDS = 120


class AnswerClaimError(ValueError):
    """Base exception for answer claim and concurrency conflicts."""


class AnswerAlreadyProcessedError(AnswerClaimError):
    """Raised when an answer has already been evaluated or skipped."""


class AnswerCurrentlyProcessingError(AnswerClaimError):
    """Raised when another request holds an active, non-expired claim on the answer."""


class AnswerClaimLostError(AnswerClaimError):
    """Raised when a worker's claim expired and was superseded before final commit."""


class AnswerDatabaseContentionError(RuntimeError):
    """Raised when transient SQLite database locks persist beyond bounded retries."""


def get_answer_claim_timeout_seconds() -> int:
    """Returns the configurable stale-claim recovery timeout in seconds."""
    val = getattr(
        settings,
        "ANSWER_CLAIM_TIMEOUT_SECONDS",
        DEFAULT_ANSWER_CLAIM_TIMEOUT_SECONDS,
    )
    try:
        return max(1, int(val))
    except (TypeError, ValueError):
        return DEFAULT_ANSWER_CLAIM_TIMEOUT_SECONDS


def _is_sqlite_lock_error(exc: OperationalError) -> bool:
    """Checks whether an OperationalError is a transient SQLite lock contention error."""
    msg = str(exc).lower()
    return "database is locked" in msg or "database table is locked" in msg


def _run_with_sqlite_lock_retry(
    operation: Callable[[], T],
    max_retries: int = 4,
    base_delay: float = 0.05,
) -> T:
    """
    Executes a short database operation with bounded exponential backoff retries
    strictly for transient SQLite lock errors ('database is locked').
    Non-lock OperationalErrors are re-raised immediately.
    """
    for attempt in range(max_retries + 1):
        try:
            return operation()
        except OperationalError as exc:
            if not _is_sqlite_lock_error(exc):
                raise
            if attempt >= max_retries:
                logger.error(
                    "SQLite lock contention exhausted %d retries: %s",
                    max_retries,
                    exc,
                )
                raise AnswerDatabaseContentionError(
                    "Database is temporarily busy processing another request. Please try again."
                ) from exc
            sleep_sec = base_delay * (2 ** attempt) + random.uniform(0.0, 0.02)
            time.sleep(sleep_sec)
    raise AnswerDatabaseContentionError(
        "Database is temporarily busy processing another request. Please try again."
    )


def acquire_answer_claim(session: InterviewSession, answer_id: int) -> str:
    """
    Atomically transitions an Answer from 'unclaimed', 'failed', or stale 'processing'
    to 'processing' with a unique UUID claim token using a single conditional UPDATE.
    """
    token = uuid.uuid4().hex
    now = timezone.now()
    timeout_seconds = get_answer_claim_timeout_seconds()
    stale_cutoff = now - timedelta(seconds=timeout_seconds)

    claimed = _run_with_sqlite_lock_retry(
        lambda: (
            Answer.objects.filter(
                id=answer_id,
                session=session,
                processed=False,
            )
            .filter(
                Q(processing_state__in=["unclaimed", "failed"])
                | Q(processing_state="processing", claimed_at__isnull=True)
                | Q(processing_state="processing", claimed_at__lt=stale_cutoff)
            )
            .update(
                processing_state="processing",
                claim_token=token,
                claimed_at=now,
            )
        )
    )

    if claimed == 1:
        return token

    current = (
        Answer.objects.filter(id=answer_id, session=session)
        .values("processed", "processing_state")
        .first()
    )
    if not current:
        raise ValueError(f"Answer #{answer_id} not found in session #{session.id}.")
    if current["processed"] or current["processing_state"] == "processed":
        raise AnswerAlreadyProcessedError(
            f"Answer #{answer_id} has already been processed."
        )
    raise AnswerCurrentlyProcessingError(
        f"Answer #{answer_id} is currently being processed by another request."
    )


def renew_answer_claim(answer_id: int, token: str) -> bool:
    """
    Refreshes claimed_at for an active claim owned by `token`.
    Used between long-running stages (e.g. after Whisper transcription before Groq evaluation).
    Returns True if the claim is still owned and renewed, False if the claim was lost.
    """
    now = timezone.now()
    updated = _run_with_sqlite_lock_retry(
        lambda: Answer.objects.filter(
            id=answer_id,
            processed=False,
            processing_state="processing",
            claim_token=token,
        ).update(claimed_at=now)
    )
    return updated == 1


def release_answer_claim_on_failure(answer_id: int, token: str) -> bool:
    """
    Releases a claim back to 'failed' state only if still owned by `token`
    and not yet processed.
    """
    updated = _run_with_sqlite_lock_retry(
        lambda: Answer.objects.filter(
            id=answer_id,
            processed=False,
            processing_state="processing",
            claim_token=token,
        ).update(
            processing_state="failed",
            claim_token="",
            claimed_at=None,
        )
    )
    return updated == 1


def _cleanup_saved_audio(storage, saved_audio_name: Optional[str]) -> None:
    """Safely deletes a temporary/uncommitted audio file created by the current request."""
    if not saved_audio_name or not storage:
        return
    try:
        if storage.exists(saved_audio_name):
            storage.delete(saved_audio_name)
    except Exception as cleanup_err:
        logger.warning(
            "Failed to delete uncommitted audio file '%s': %s",
            saved_audio_name,
            cleanup_err,
        )


def _transcribe_saved_audio(storage, saved_audio_name: str) -> str:
    """
    Transcribes a saved audio file using its local filesystem path when supported,
    or falls back to a temporary file copy for non-local storage backends.
    """
    try:
        local_path = storage.path(saved_audio_name)
        return transcribe_audio(local_path)
    except (NotImplementedError, AttributeError):
        ext = os.path.splitext(saved_audio_name)[1] or ".wav"
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp_file:
                temp_path = tmp_file.name
                with storage.open(saved_audio_name, "rb") as src:
                    for chunk in iter(lambda: src.read(65536), b""):
                        tmp_file.write(chunk)
            return transcribe_audio(temp_path)
        finally:
            if temp_path and os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except OSError:
                    pass


def submit_candidate_answer(
    session: InterviewSession,
    answer_id: int,
    answer_text: str = "",
    audio_file=None,
) -> Tuple[Answer, bool]:
    """
    Processes a candidate's text or voice answer using an atomic claim-evaluate-commit lifecycle:
    1. Acquires an exclusive claim on the Answer via a single conditional UPDATE.
    2. Saves uploaded audio under a claim-unique filename without mutating Answer DB fields.
    3. Runs Whisper transcription (if needed) and renews the claim before Groq evaluation.
    4. Evaluates the answer via analyze_transcript() outside any database transaction.
    5. Atomically commits the evaluation result only if the claim token still matches.
    6. On any failure or lost claim, deletes only the current request's audio file and
       transitions the claim to 'failed' (if still owned by this request's token).
    """
    # Step 1: Acquire atomic claim before any file I/O or AI evaluation
    token = acquire_answer_claim(session=session, answer_id=answer_id)

    ans = Answer.objects.select_related("question").filter(id=answer_id, session=session).first()
    if not ans:
        release_answer_claim_on_failure(answer_id, token)
        raise ValueError(f"Answer #{answer_id} not found in session #{session.id}.")

    storage = ans.audio_file.storage
    previous_audio_name = ans.audio_file.name if (ans.audio_file and ans.audio_file.name) else None
    saved_audio_name: Optional[str] = None
    final_text = (answer_text or "").strip()

    try:
        # Step 2: Persist uploaded audio to storage under a claim-isolated filename
        if audio_file is not None:
            orig_name = getattr(audio_file, "name", "") or "audio.wav"
            ext = os.path.splitext(orig_name)[1].lower() or ".wav"
            isolated_rel_path = f"voice_answers/ans_{ans.id}_{token[:12]}{ext}"
            saved_audio_name = storage.save(isolated_rel_path, audio_file)

        # Step 3: Transcribe audio if text was not provided
        if saved_audio_name and not final_text:
            try:
                transcribed = _transcribe_saved_audio(storage, saved_audio_name)
            except Exception as exc:
                logger.exception(
                    "Whisper transcription failed for Answer #%s: %s",
                    ans.id,
                    exc,
                )
                transcribed = None
            final_text = transcribed or "[Voice answer could not be transcribed]"

            # Renew claim timestamp after Whisper finishes so Groq evaluation has a fresh window
            if not renew_answer_claim(ans.id, token):
                raise AnswerClaimLostError(
                    f"Claim on Answer #{ans.id} expired during audio transcription."
                )

        # Step 4: Run NLP / Groq / Resume-Grounded evaluation outside DB transaction
        result = analyze_transcript(
            text=final_text,
            question=ans.question,
            resume=session.resume,
            job_description=session.job_description,
        )

        # Step 5: Atomic final commit verifying claim_token ownership
        def _commit_evaluation() -> bool:
            with transaction.atomic():
                final_audio_val = (
                    saved_audio_name
                    if saved_audio_name
                    else (previous_audio_name or "")
                )
                updated = Answer.objects.filter(
                    id=ans.id,
                    session=session,
                    processed=False,
                    processing_state="processing",
                    claim_token=token,
                ).update(
                    answer_text=final_text,
                    audio_file=final_audio_val,
                    score=result.get("score"),
                    feedback=result.get("feedback", ""),
                    improvement_tips=result.get("improvement_tips", []),
                    resume_grounding=result.get("resume_grounding"),
                    processed=True,
                    processing_state="processed",
                    claim_token="",
                    claimed_at=None,
                )
                if updated == 0:
                    raise AnswerClaimLostError(
                        f"Claim ownership lost for Answer #{ans.id}; aborting commit."
                    )

                remaining = session.answers.filter(processed=False).exists()
                completed_now = not remaining
                if completed_now:
                    now_ts = timezone.now()
                    InterviewSession.objects.filter(
                        id=session.id, completed=False
                    ).update(
                        completed=True,
                        completed_at=now_ts,
                    )
                    session.completed = True
                    session.completed_at = now_ts
                return completed_now

        is_completed = _run_with_sqlite_lock_retry(_commit_evaluation)
        if is_completed:
            finalize_session_video_metrics(session)

    except Exception as exc:
        # Clean up only the audio file created by this request
        _cleanup_saved_audio(storage, saved_audio_name)

        # Release the claim to 'failed' only if still owned by this request's token
        if not isinstance(exc, AnswerClaimLostError):
            try:
                release_answer_claim_on_failure(ans.id, token)
            except Exception as release_err:
                logger.exception(
                    "Failed to release claim on Answer #%s after error: %s",
                    ans.id,
                    release_err,
                )
        raise

    # If this winning commit replaced an older audio file on the same Answer, remove the old file
    if saved_audio_name and previous_audio_name and previous_audio_name != saved_audio_name:
        _cleanup_saved_audio(storage, previous_audio_name)

    ans.refresh_from_db()
    return ans, is_completed


def skip_candidate_question(
    session: InterviewSession,
    answer_id: Optional[int] = None,
) -> Tuple[Optional[Answer], bool]:
    """
    Atomically marks the current or specified unanswered question as skipped (score=0, processed=True).
    Rejects skipping if the answer is actively being processed by an in-flight submission.
    """
    if answer_id is not None:
        ans = session.answers.filter(id=answer_id).first()
        if not ans:
            raise ValueError(f"Answer #{answer_id} not found in session #{session.id}.")
    else:
        ans = session.answers.filter(processed=False).order_by("index").first()
        if not ans:
            return None, True

    now = timezone.now()
    stale_cutoff = now - timedelta(seconds=get_answer_claim_timeout_seconds())

    def _skip_atomic() -> bool:
        with transaction.atomic():
            updated = (
                Answer.objects.filter(
                    id=ans.id,
                    session=session,
                    processed=False,
                )
                .filter(
                    Q(processing_state__in=["unclaimed", "failed"])
                    | Q(processing_state="processing", claimed_at__isnull=True)
                    | Q(processing_state="processing", claimed_at__lt=stale_cutoff)
                )
                .update(
                    answer_text="[Skipped]",
                    score=0,
                    feedback="Question was skipped.",
                    processed=True,
                    processing_state="processed",
                    claim_token="",
                    claimed_at=None,
                )
            )
            if updated == 0:
                current = (
                    Answer.objects.filter(id=ans.id, session=session)
                    .values("processed", "processing_state")
                    .first()
                )
                if not current:
                    raise ValueError(f"Answer #{ans.id} not found in session #{session.id}.")
                if current["processed"] or current["processing_state"] == "processed":
                    raise AnswerAlreadyProcessedError(
                        f"Answer #{ans.id} has already been processed."
                    )
                raise AnswerCurrentlyProcessingError(
                    f"Answer #{ans.id} is currently being processed and cannot be skipped."
                )

            remaining = session.answers.filter(processed=False).exists()
            completed_now = not remaining
            if completed_now:
                now_ts = timezone.now()
                InterviewSession.objects.filter(
                    id=session.id, completed=False
                ).update(
                    completed=True,
                    completed_at=now_ts,
                )
                session.completed = True
                session.completed_at = now_ts
            return completed_now

    is_completed = _run_with_sqlite_lock_retry(_skip_atomic)
    if is_completed:
        finalize_session_video_metrics(session)
    ans.refresh_from_db()
    return ans, is_completed


def end_candidate_session(session: InterviewSession) -> InterviewSession:
    """
    Immediately terminates an active interview session, flushing any in-memory video stats.
    """
    finalize_session_video_metrics(session)
    now_ts = timezone.now()
    _run_with_sqlite_lock_retry(
        lambda: InterviewSession.objects.filter(id=session.id, completed=False).update(
            completed=True,
            completed_at=now_ts,
        )
    )
    session.refresh_from_db()
    return session
