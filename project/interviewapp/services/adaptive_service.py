"""
Adaptive interview decision engine and session-creation foundation.

Milestone 1 scope:
- Pure deterministic decision engine (`decide_next_adaptive_step`, `is_follow_up_eligible`,
  `compute_next_main_difficulty`) with zero Groq imports and zero database writes.
- Adaptive session initialization (`create_adaptive_session`) that creates only the first
  main question (index=1, parent_answer=None) without pre-allocating unanswered placeholders.

Reliability & Recovery Strategy (for Milestone 2 API integration):
1. Duplicate answer submissions:
   `submit_candidate_answer(..., auto_complete=False)` uses atomic `acquire_answer_claim`
   with a UUID `claim_token` and `processing_state` transitions, rejecting concurrent or
   already-processed submissions with `AnswerCurrentlyProcessingError` / `AnswerAlreadyProcessedError`.
2. Concurrent requests attempting to generate the next question:
   Next-question persistence must acquire a short `transaction.atomic()` lock on the
   `InterviewSession` row (`select_for_update()` on Postgres; conditional `index = last_index + 1`
   with `unique_together = ('session', 'index')` on SQLite) and re-check whether an unprocessed
   `Answer` at `index > last_answer.index` (or a `follow_ups` row) already exists before inserting.
3. Duplicate follow-up generation:
   Enforced both by `is_follow_up_eligible()` (`parent_answer_id is None` and `not follow_ups.exists()`)
   and by checking `Answer.objects.filter(parent_answer=last_answer).exists()` inside the atomic
   append transaction.
4. Groq failures after an answer has already been evaluated:
   Because `submit_candidate_answer(..., auto_complete=False)` commits the evaluated `Answer`
   before any next-question Groq call is made, the candidate's evaluated answer is never rolled back.
   If next-question generation fails (timeout/rate-limit) and stub fallback is disabled or fails,
   the session remains `completed=False` with all prior answers preserved; a subsequent retry
   (e.g., `GET /next-question/` or a dedicated retry path) can inspect the latest processed `Answer`,
   re-run `decide_next_adaptive_step()` deterministically, and append the missing next `Answer`.
"""

from dataclasses import dataclass
import logging
from typing import Optional, Tuple, Union

from django.db import IntegrityError, transaction
from django.utils import timezone

from ..models import Answer, GeneratedQuestion, InterviewSession, SessionQuestion
from .answer_service import (
    AnswerAlreadyProcessedError,
    skip_candidate_question,
    submit_candidate_answer,
)
from .session_service import ROLE_MAP, generate_question_stub
from .video_service import finalize_session_video_metrics

logger = logging.getLogger(__name__)

EXPLICIT_SKIP_TEXT = "[Skipped]"
TRANSCRIPTION_FAILED_TEXT = "[Voice answer could not be transcribed]"


def is_hr_role(role: Optional[str]) -> bool:
    """
    Returns True for HR-focused interview roles ('hr', 'Human Resources', etc.),
    normalizing case and whitespace.
    """
    normalized = " ".join((role or "").strip().lower().split())
    return normalized == "hr" or "human resources" in normalized


@dataclass(frozen=True)
class AdaptivePolicy:
    """Configurable, testable scoring and difficulty bounds for V1 adaptive rules."""

    follow_up_min_score: float = 40.0
    follow_up_max_score: float = 75.0
    difficulty_up_threshold: float = 75.0
    difficulty_down_threshold: float = 40.0
    min_difficulty: int = 1
    max_difficulty: int = 5


DEFAULT_ADAPTIVE_POLICY = AdaptivePolicy()


@dataclass(frozen=True)
class AdaptiveStepInput:
    """
    Explicit, DB-free input contract for the adaptive decision engine.
    The orchestration layer is responsible for reading these values from the DB.
    """

    role: str
    max_main_questions: int
    main_count: int
    current_difficulty: int
    score: Optional[float]
    is_skipped: bool
    is_follow_up: bool
    has_followup: bool
    answer_id: Optional[int] = None


@dataclass(frozen=True)
class AdaptiveDecision:
    """Structured output returned by `decide_next_adaptive_step`."""

    action: str  # "follow_up" | "next_main" | "completed"
    next_difficulty: int
    parent_answer_id: Optional[int]
    reason: str


def _clamp_difficulty(value: int, policy: AdaptivePolicy = DEFAULT_ADAPTIVE_POLICY) -> int:
    return max(policy.min_difficulty, min(policy.max_difficulty, int(value)))


def is_skipped_answer(answer_or_text: Union[Answer, str, None]) -> bool:
    """
    Returns True ONLY when the candidate explicitly skipped the question ('[Skipped]').
    Empty responses, transcription failures ('[Voice answer could not be transcribed]'),
    and arbitrary candidate text are NOT classified as explicit skips.
    """
    if isinstance(answer_or_text, str) or answer_or_text is None:
        raw_text = answer_or_text or ""
    else:
        raw_text = getattr(answer_or_text, "answer_text", "") or ""
    return raw_text.strip() == EXPLICIT_SKIP_TEXT


def is_follow_up_eligible(
    *,
    is_follow_up: bool,
    has_followup: bool,
    is_skipped: bool,
    score: Optional[float],
    policy: AdaptivePolicy = DEFAULT_ADAPTIVE_POLICY,
) -> Tuple[bool, str]:
    """
    Pure eligibility check for whether the evaluated answer may receive a follow-up question.
    Enforces at most one follow-up per main question and blocks follow-ups on skipped answers.
    """
    if is_follow_up:
        return False, "already_follow_up"

    if has_followup:
        return False, "follow_up_already_used"

    if is_skipped:
        return False, "skipped_answer"

    if score is None:
        return False, "missing_score"

    numeric_score = float(score)
    if policy.follow_up_min_score <= numeric_score < policy.follow_up_max_score:
        return True, "score_in_follow_up_band"

    return False, "score_outside_follow_up_band"


def compute_next_main_difficulty(
    *,
    role: str,
    current_difficulty: int,
    score: Optional[float],
    is_skipped: bool,
    policy: AdaptivePolicy = DEFAULT_ADAPTIVE_POLICY,
) -> int:
    """
    Pure difficulty-adaptation rule for the next main question (clamped to 1..5).
    HR-focused sessions keep difficulty unchanged.
    """
    clamped_current = _clamp_difficulty(current_difficulty or 3, policy)

    if is_hr_role(role):
        return clamped_current

    if is_skipped:
        return _clamp_difficulty(clamped_current - 1, policy)

    numeric_score = float(score) if score is not None else 0.0

    if numeric_score >= policy.difficulty_up_threshold:
        return _clamp_difficulty(clamped_current + 1, policy)
    if numeric_score < policy.difficulty_down_threshold:
        return _clamp_difficulty(clamped_current - 1, policy)
    return clamped_current


def decide_next_adaptive_step(
    step_input: AdaptiveStepInput,
    *,
    policy: AdaptivePolicy = DEFAULT_ADAPTIVE_POLICY,
) -> AdaptiveDecision:
    """
    Deterministic adaptive orchestration decision function.
    Performs zero Groq calls, zero ORM queries, and zero database writes.
    """
    eligible, reason = is_follow_up_eligible(
        is_follow_up=step_input.is_follow_up,
        has_followup=step_input.has_followup,
        is_skipped=step_input.is_skipped,
        score=step_input.score,
        policy=policy,
    )
    if eligible:
        return AdaptiveDecision(
            action="follow_up",
            next_difficulty=_clamp_difficulty(step_input.current_difficulty or 3, policy),
            parent_answer_id=step_input.answer_id,
            reason=reason,
        )

    next_diff = compute_next_main_difficulty(
        role=step_input.role,
        current_difficulty=step_input.current_difficulty,
        score=step_input.score,
        is_skipped=step_input.is_skipped,
        policy=policy,
    )
    max_main = int(step_input.max_main_questions or 0)
    if step_input.main_count >= max_main:
        return AdaptiveDecision(
            action="completed",
            next_difficulty=next_diff,
            parent_answer_id=None,
            reason="max_main_questions_reached",
        )

    return AdaptiveDecision(
        action="next_main",
        next_difficulty=next_diff,
        parent_answer_id=None,
        reason=reason,
    )


def validate_adaptive_session_params(
    raw_role: str,
    job_role: str,
    difficulty: int = 3,
    max_main_questions: int = 5,
) -> Tuple[str, str, int, int]:
    """Validates adaptive session inputs using existing Standard session conventions."""
    normalized_role = (raw_role or "tech").strip().lower()
    if normalized_role not in ROLE_MAP:
        raise ValueError(f"Invalid role '{raw_role}'. Must be one of: {', '.join(sorted(ROLE_MAP))}.")

    clean_job_role = (job_role or "").strip() or "Software Engineer"
    if len(clean_job_role) > 100:
        raise ValueError("Job role must be 100 characters or fewer.")

    try:
        clean_diff = int(difficulty)
    except (TypeError, ValueError) as exc:
        raise ValueError("Difficulty must be an integer between 1 and 5.") from exc
    if clean_diff < 1 or clean_diff > 5:
        raise ValueError("Difficulty must be between 1 and 5.")

    try:
        clean_count = int(max_main_questions)
    except (TypeError, ValueError) as exc:
        raise ValueError("max_main_questions must be an integer between 1 and 30.") from exc
    if clean_count < 1 or clean_count > 30:
        raise ValueError("max_main_questions must be between 1 and 30.")

    return normalized_role, clean_job_role, clean_diff, clean_count


def create_adaptive_session(
    user,
    raw_role: str = "tech",
    job_role: str = "Software Engineer",
    difficulty: int = 3,
    max_main_questions: int = 5,
) -> Tuple[InterviewSession, int]:
    """
    Creates an InterviewSession with state='adaptive', generates only the first main
    question (index=1, parent_answer=None), and creates its Answer and SessionQuestion.
    Does NOT pre-allocate unanswered Answer placeholders.
    """
    from ..qgen_groq import generate_questions_groq, signature_of_text

    norm_role, clean_job_role, clean_diff, clean_max_main = validate_adaptive_session_params(
        raw_role=raw_role,
        job_role=job_role,
        difficulty=difficulty,
        max_main_questions=max_main_questions,
    )
    role_for_prompt = ROLE_MAP[norm_role]

    prev_questions = list(
        SessionQuestion.objects.filter(session__user=user, session__role=norm_role)
        .order_by("-id")
        .values_list("question__text", flat=True)
        .distinct()[:15]
    )

    question_source = "llm"
    try:
        llm_questions = generate_questions_groq(
            role=role_for_prompt,
            job_role=clean_job_role,
            n=1,
            difficulty=clean_diff,
            previous_questions=prev_questions,
        )
    except Exception as exc:
        logger.exception("Adaptive first-question Groq generation error: %s", exc)
        llm_questions = []

    qobj = (llm_questions or [None])[0]
    if not qobj or not (qobj.get("text") or "").strip():
        qobj = generate_question_stub(norm_role, difficulty=clean_diff, job_role=clean_job_role)
        question_source = "template"

    q_text = (qobj.get("text") or "").strip()
    sig = signature_of_text(q_text)

    with transaction.atomic():
        session = InterviewSession.objects.create(
            user=user,
            role=norm_role,
            job_role=clean_job_role,
            difficulty=clean_diff,
            state="adaptive",
            max_main_questions=clean_max_main,
            total_questions=1,
            current_index=1,
            total_score=None,
        )

        qrow, _ = GeneratedQuestion.objects.get_or_create(
            signature=sig,
            defaults={
                "role": norm_role,
                "difficulty": qobj.get("difficulty", clean_diff),
                "text": q_text,
                "keywords": qobj.get("keywords", ""),
                "source": question_source,
            },
        )
        if qrow.role != norm_role:
            qrow.role = norm_role
            qrow.save(update_fields=["role"])

        Answer.objects.create(
            session=session,
            question=qrow,
            parent_answer=None,
            index=1,
        )
        SessionQuestion.objects.create(
            session=session,
            question=qrow,
            order=1,
            asked=True,
        )

    return session, 1


class AdaptiveProgressionError(ValueError):
    """Base error for adaptive session progression validation."""


class AdaptiveAnswerNotFoundError(AdaptiveProgressionError):
    """Raised when the requested answer_id does not belong to the session."""


class AdaptiveSequentialOrderError(AdaptiveProgressionError):
    """Raised when a candidate attempts to answer out of sequential order."""


class AdaptiveNoPendingQuestionError(AdaptiveProgressionError):
    """Raised when no unprocessed question exists and session is already complete."""


@dataclass(frozen=True)
class AdaptiveProgressionResult:
    """Structured result returned by adaptive answer submission / skip orchestration."""

    answer: Answer
    is_session_completed: bool
    next_answer: Optional[Answer]
    next_question_kind: Optional[str]  # "main" | "follow_up" | None
    main_questions_count: int
    max_main_questions: int
    total_interactions: int
    idempotent_replay: bool = False


def _generate_follow_up_stub(
    original_question_text: str,
    difficulty: int,
    raw_role: str,
) -> dict:
    """Deterministic fallback follow-up question when Groq is unavailable."""
    snippet = (original_question_text or "").strip().rstrip("?")
    if len(snippet) > 90:
        snippet = snippet[:87] + "..."
    text = (
        f"Building on your previous answer about \"{snippet}\", "
        "can you walk through a concrete example, edge case, or trade-off to support your reasoning?"
        if snippet
        else "Can you elaborate on your previous answer with a concrete example or trade-off?"
    )
    return {
        "text": text,
        "keywords": "example,trade-off,reasoning",
        "difficulty": difficulty,
        "role": raw_role,
    }


def _generate_next_question_payload(
    *,
    session: InterviewSession,
    last_answer: Answer,
    decision: AdaptiveDecision,
    previous_questions: list,
) -> Tuple[dict, str]:
    """
    Generates 1 question dict outside any database transaction, with safe fallback
    to role-aware stubs so Groq outages never leave the session deadlocked.
    """
    from ..qgen_groq import generate_follow_up_question_groq, generate_questions_groq

    role_for_prompt = ROLE_MAP.get((session.role or "").strip().lower(), session.role or "Technical")
    if decision.action == "follow_up":
        orig_text = last_answer.question.text if last_answer.question else ""
        qobj = None
        try:
            qobj = generate_follow_up_question_groq(
                original_question_text=orig_text,
                candidate_answer=last_answer.answer_text or "",
                role=role_for_prompt,
                job_role=session.job_role,
                difficulty=decision.next_difficulty,
                previous_questions=previous_questions,
            )
        except Exception as exc:
            logger.exception("Adaptive follow-up Groq generation error: %s", exc)
            qobj = None

        if qobj and (qobj.get("text") or "").strip():
            return qobj, "llm"
        return _generate_follow_up_stub(orig_text, decision.next_difficulty, session.role), "template"

    # action == "next_main"
    llm_questions = []
    try:
        llm_questions = generate_questions_groq(
            role=role_for_prompt,
            job_role=session.job_role,
            n=1,
            difficulty=decision.next_difficulty,
            previous_questions=previous_questions,
        )
    except Exception as exc:
        logger.exception("Adaptive next-main Groq generation error: %s", exc)
        llm_questions = []

    qobj = (llm_questions or [None])[0]
    if qobj and (qobj.get("text") or "").strip():
        return qobj, "llm"

    stub = generate_question_stub(
        session.role,
        difficulty=decision.next_difficulty,
        job_role=session.job_role,
    )
    return stub, "template"


def _build_step_input_from_db(
    session: InterviewSession,
    last_answer: Answer,
) -> AdaptiveStepInput:
    """Reads all DB facts required by `decide_next_adaptive_step`."""
    main_count = session.answers.filter(parent_answer__isnull=True).count()
    has_followup = Answer.objects.filter(parent_answer_id=last_answer.id).exists()
    current_diff = (
        last_answer.question.difficulty
        if getattr(last_answer, "question", None) is not None
        else session.difficulty
    )
    return AdaptiveStepInput(
        role=session.role,
        max_main_questions=session.max_main_questions,
        main_count=main_count,
        current_difficulty=current_diff,
        score=last_answer.score,
        is_skipped=is_skipped_answer(last_answer),
        is_follow_up=last_answer.parent_answer_id is not None,
        has_followup=has_followup,
        answer_id=last_answer.id,
    )


def advance_adaptive_session_from_answer(
    session: InterviewSession,
    last_answer: Answer,
    *,
    idempotent_replay: bool = False,
) -> AdaptiveProgressionResult:
    """
    Idempotently advances an adaptive session from an already-evaluated `last_answer`.
    - Checks if the next answer or completion has already been committed.
    - Runs pure `decide_next_adaptive_step()`.
    - Generates any required question OUTSIDE any database transaction.
    - Commits the next Answer + SessionQuestion (or completion) atomically, re-checking
      uniqueness under lock so concurrent retries never create duplicate questions.
    """
    from ..qgen_groq import signature_of_text

    # Fast-path idempotency check before any Groq call
    session.refresh_from_db()
    existing_next = (
        session.answers.select_related("question")
        .filter(index=last_answer.index + 1)
        .first()
    )
    if existing_next:
        main_count = session.answers.filter(parent_answer__isnull=True).count()
        total_interactions = session.answers.count()
        next_kind = "follow_up" if existing_next.parent_answer_id is not None else "main"
        return AdaptiveProgressionResult(
            answer=last_answer,
            is_session_completed=False,
            next_answer=existing_next,
            next_question_kind=next_kind,
            main_questions_count=main_count,
            max_main_questions=session.max_main_questions,
            total_interactions=total_interactions,
            idempotent_replay=True,
        )

    if session.completed:
        main_count = session.answers.filter(parent_answer__isnull=True).count()
        total_interactions = session.answers.count()
        return AdaptiveProgressionResult(
            answer=last_answer,
            is_session_completed=True,
            next_answer=None,
            next_question_kind=None,
            main_questions_count=main_count,
            max_main_questions=session.max_main_questions,
            total_interactions=total_interactions,
            idempotent_replay=True,
        )

    step_input = _build_step_input_from_db(session, last_answer)
    decision = decide_next_adaptive_step(step_input)

    if decision.action == "completed":
        now_ts = timezone.now()
        with transaction.atomic():
            InterviewSession.objects.filter(id=session.id, completed=False).update(
                completed=True,
                completed_at=now_ts,
            )
        session.refresh_from_db()
        finalize_session_video_metrics(session)
        main_count = session.answers.filter(parent_answer__isnull=True).count()
        total_interactions = session.answers.count()
        return AdaptiveProgressionResult(
            answer=last_answer,
            is_session_completed=True,
            next_answer=None,
            next_question_kind=None,
            main_questions_count=main_count,
            max_main_questions=session.max_main_questions,
            total_interactions=total_interactions,
            idempotent_replay=idempotent_replay,
        )

    # Generate next question OUTSIDE any database transaction
    previous_questions = list(
        SessionQuestion.objects.filter(session=session)
        .order_by("order")
        .values_list("question__text", flat=True)
    )
    qobj, question_source = _generate_next_question_payload(
        session=session,
        last_answer=last_answer,
        decision=decision,
        previous_questions=previous_questions,
    )
    q_text = (qobj.get("text") or "").strip()
    sig = signature_of_text(q_text)
    next_index = last_answer.index + 1

    # Short atomic commit with re-checks for concurrency & budget invariants
    next_ans = None
    completed_on_race = False
    try:
        with transaction.atomic():
            locked_session = InterviewSession.objects.select_for_update().get(id=session.id)

            if locked_session.completed:
                completed_on_race = True
            else:
                existing_next = (
                    locked_session.answers.select_related("question")
                    .filter(index=next_index)
                    .first()
                )
                if existing_next:
                    next_ans = existing_next
                    idempotent_replay = True
                elif (
                    decision.action == "follow_up"
                    and Answer.objects.filter(parent_answer_id=last_answer.id).exists()
                ):
                    existing_fu = (
                        locked_session.answers.select_related("question")
                        .filter(parent_answer_id=last_answer.id)
                        .first()
                    )
                    next_ans = existing_fu
                    idempotent_replay = True
                elif (
                    decision.action == "next_main"
                    and locked_session.answers.filter(parent_answer__isnull=True).count()
                    >= locked_session.max_main_questions
                ):
                    now_ts = timezone.now()
                    InterviewSession.objects.filter(id=locked_session.id, completed=False).update(
                        completed=True,
                        completed_at=now_ts,
                    )
                    completed_on_race = True
                else:
                    qrow, _ = GeneratedQuestion.objects.get_or_create(
                        signature=sig,
                        defaults={
                            "role": locked_session.role,
                            "difficulty": qobj.get("difficulty", decision.next_difficulty),
                            "text": q_text,
                            "keywords": qobj.get("keywords", ""),
                            "source": question_source,
                        },
                    )
                    next_ans = Answer.objects.create(
                        session=locked_session,
                        question=qrow,
                        parent_answer_id=decision.parent_answer_id,
                        index=next_index,
                    )
                    SessionQuestion.objects.create(
                        session=locked_session,
                        question=qrow,
                        order=next_index,
                        asked=True,
                    )
                    total_count = locked_session.answers.count()
                    InterviewSession.objects.filter(id=locked_session.id).update(
                        total_questions=total_count,
                        current_index=next_index,
                    )
    except IntegrityError:
        # Concurrent insert hit unique_together ('session', 'index'); return winner's row
        next_ans = (
            session.answers.select_related("question")
            .filter(index=next_index)
            .first()
        )
        idempotent_replay = True

    session.refresh_from_db()
    main_count = session.answers.filter(parent_answer__isnull=True).count()
    total_interactions = session.answers.count()

    if completed_on_race or (next_ans is None and session.completed):
        finalize_session_video_metrics(session)
        return AdaptiveProgressionResult(
            answer=last_answer,
            is_session_completed=True,
            next_answer=None,
            next_question_kind=None,
            main_questions_count=main_count,
            max_main_questions=session.max_main_questions,
            total_interactions=total_interactions,
            idempotent_replay=idempotent_replay,
        )

    next_kind = (
        "follow_up"
        if (next_ans is not None and next_ans.parent_answer_id is not None)
        else ("main" if next_ans is not None else None)
    )
    return AdaptiveProgressionResult(
        answer=last_answer,
        is_session_completed=False,
        next_answer=next_ans,
        next_question_kind=next_kind,
        main_questions_count=main_count,
        max_main_questions=session.max_main_questions,
        total_interactions=total_interactions,
        idempotent_replay=idempotent_replay,
    )


def _resolve_target_or_replay(
    session: InterviewSession,
    answer_id: Optional[int],
) -> Tuple[Optional[Answer], Optional[AdaptiveProgressionResult]]:
    """
    Resolves the target unprocessed Answer or detects an idempotent retry / crash-recovery
    for the most recently processed Answer.
    """
    current_unanswered = (
        session.answers.select_related("question")
        .filter(processed=False)
        .order_by("index")
        .first()
    )

    if answer_id is not None:
        target_ans = session.answers.select_related("question").filter(id=answer_id).first()
        if not target_ans:
            raise AdaptiveAnswerNotFoundError("Answer not found in this session.")

        if target_ans.processed:
            has_later_processed = session.answers.filter(
                processed=True, index__gt=target_ans.index
            ).exists()
            if has_later_processed:
                raise AnswerAlreadyProcessedError(
                    "This question has already been answered and processed."
                )
            # Latest processed answer: idempotent replay or post-evaluation recovery
            result = advance_adaptive_session_from_answer(
                session, target_ans, idempotent_replay=True
            )
            return None, result

        if current_unanswered is None or target_ans.id != current_unanswered.id:
            raise AdaptiveSequentialOrderError(
                "Questions must be answered in sequential order."
            )
        return target_ans, None

    if current_unanswered is not None:
        return current_unanswered, None

    # No unprocessed answers exist and session isn't completed -> recover from latest processed
    latest_processed = (
        session.answers.select_related("question")
        .filter(processed=True)
        .order_by("-index")
        .first()
    )
    if latest_processed and not session.completed:
        result = advance_adaptive_session_from_answer(
            session, latest_processed, idempotent_replay=True
        )
        return None, result

    raise AdaptiveNoPendingQuestionError("No unprocessed questions remaining in this session.")


def submit_adaptive_answer(
    session: InterviewSession,
    *,
    answer_id: Optional[int] = None,
    answer_text: str = "",
    audio_file=None,
) -> AdaptiveProgressionResult:
    """
    Evaluates an adaptive interview answer via `submit_candidate_answer(..., auto_complete=False)`
    and advances the session deterministically with full idempotency and concurrency safety.
    """
    target_ans, replay_result = _resolve_target_or_replay(session, answer_id)
    if replay_result is not None:
        return replay_result

    evaluated_ans, _ = submit_candidate_answer(
        session=session,
        answer_id=target_ans.id,
        answer_text=answer_text,
        audio_file=audio_file,
        auto_complete=False,
    )
    return advance_adaptive_session_from_answer(session, evaluated_ans)


def skip_adaptive_question(
    session: InterviewSession,
    *,
    answer_id: Optional[int] = None,
) -> AdaptiveProgressionResult:
    """
    Skips the current adaptive question via `skip_candidate_question(..., auto_complete=False)`
    and advances the session deterministically.
    """
    target_ans, replay_result = _resolve_target_or_replay(session, answer_id)
    if replay_result is not None:
        return replay_result

    skipped_ans, _ = skip_candidate_question(
        session=session,
        answer_id=target_ans.id,
        auto_complete=False,
    )
    return advance_adaptive_session_from_answer(session, skipped_ans)


