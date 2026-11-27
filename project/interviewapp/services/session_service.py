import logging
from typing import Dict, List, Optional, Tuple
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from ..models import Answer, GeneratedQuestion, InterviewSession, Resume, SessionQuestion
from ..qgen_groq import (
    generate_questions_groq,
    generate_resume_jd_questions_groq,
    generate_session_suggestions,
    signature_of_text,
)
from ..nlp_utils import generate_expected_answer
from ..video_summary_utils import compute_video_confidence
from .resume_service import delete_candidate_resume, save_and_index_resume

logger = logging.getLogger(__name__)

try:
    from ..rag import generate_questions_with_rag, generate_resume_jd_rag_questions
    _rag_available = True
except ImportError:
    _rag_available = False

ROLE_MAP = {
    "tech": "Technical",
    "hr": "Human Resources",
    "apt": "Aptitude",
    "beh": "Behavioral",
}


try:
    from ..views_helpers import generate_question_stub
except ImportError:
    def generate_question_stub(role: str, difficulty: int = 3, job_role: str = "") -> Dict:
        """Generate a fallback template question stub when LLM quota or count is exhausted."""
        role_instructions = {
            "tech": "Explain a core technical concept or solve a practical engineering problem.",
            "hr": "Describe how to handle workplace scenarios or collaboration challenges.",
            "aptitude": "Solve a logical reasoning or quantitative problem.",
            "behavioral": "Discuss how to handle interpersonal or situational challenges.",
        }
        instruction = role_instructions.get(role.lower(), "Provide a general question related to the role.")
        role_prefix = f"{job_role.strip()} " if (job_role or "").strip() else ""
        text = f"(AI stub) {role_prefix}{role} question (difficulty {difficulty}): {instruction}"
        keywords = instruction.lower().replace(" or ", ",").replace(" ", ",")
        return {"text": text, "keywords": keywords, "difficulty": difficulty}


def populate_session_questions(
    session: InterviewSession,
    questions_data: List[Dict],
    raw_role: str,
    question_source: str,
    n: int,
    difficulty: int = 3,
    job_role: str = "",
) -> int:
    """
    Saves unique questions to database, falls back to stubs if count < n,
    and bulk-allocates Answer placeholders and SessionQuestion tracking records.
    """
    created_question_ids: List[int] = []
    created = 0
    max_attempts = max(50, n * 10)

    # 1) Save unique generated questions
    for qobj in questions_data or []:
        if created >= n:
            break
        text = (qobj.get("text") or "").strip()
        if not text:
            continue
        sig = signature_of_text(text)
        qrow, _ = GeneratedQuestion.objects.get_or_create(
            signature=sig,
            defaults={
                "role": raw_role,
                "difficulty": qobj.get("difficulty", difficulty),
                "text": text,
                "keywords": qobj.get("keywords", ""),
                "source": question_source,
            },
        )
        if qrow.role != raw_role:
            qrow.role = raw_role
            qrow.save(update_fields=["role"])

        if qrow.id not in created_question_ids:
            created_question_ids.append(qrow.id)
            created += 1

    # 2) Fallback to role-aware template stubs if needed
    attempts = 0
    while created < n and attempts < max_attempts:
        attempts += 1
        payload = generate_question_stub(raw_role, difficulty=difficulty, job_role=job_role)
        text = (payload.get("text") or "").strip()
        if not text:
            continue
        sig = signature_of_text(text)
        qrow, _ = GeneratedQuestion.objects.get_or_create(
            signature=sig,
            defaults={
                "role": raw_role,
                "difficulty": payload.get("difficulty", difficulty),
                "text": text,
                "keywords": payload.get("keywords", ""),
                "source": "template",
            },
        )
        if qrow.role != raw_role:
            qrow.role = raw_role
            qrow.save(update_fields=["role"])

        if qrow.id not in created_question_ids:
            created_question_ids.append(qrow.id)
            created += 1

    # 3) Allocate Answer placeholders and SessionQuestion in order
    session.answers.all().delete()
    idx = 1
    for qid in created_question_ids:
        qobj = GeneratedQuestion.objects.get(id=qid)
        Answer.objects.create(session=session, question=qobj, index=idx)
        SessionQuestion.objects.create(session=session, question=qobj, order=idx, asked=True)
        idx += 1

    session.total_questions = len(created_question_ids)
    session.current_index = 1 if created_question_ids else 0
    session.save(update_fields=["total_questions", "current_index"])

    return len(created_question_ids)


def create_standard_session(
    user,
    raw_role: str,
    job_role: str,
    difficulty: int = 3,
    n_questions: int = 5,
) -> Tuple[InterviewSession, int]:
    """Creates a standard role-based mock interview session directly via Groq LLM."""
    role_for_prompt = ROLE_MAP.get(raw_role.lower(), raw_role.capitalize())

    prev_questions = list(
        SessionQuestion.objects.filter(session__user=user, session__role=raw_role)
        .order_by("-id")
        .values_list("question__text", flat=True)
        .distinct()[:15]
    )

    question_source = "llm"

    try:
        llm_questions = generate_questions_groq(
            role=role_for_prompt,
            job_role=job_role,
            n=n_questions,
            difficulty=difficulty,
            previous_questions=prev_questions,
        )
    except Exception as e:
        logger.exception("Direct Groq question generation error: %s", e)
        llm_questions = []

    with transaction.atomic():
        session = InterviewSession.objects.create(
            user=user,
            total_questions=n_questions,
            role=raw_role,
            job_role=job_role,
            difficulty=difficulty,
            total_score=None,
            current_index=0,
        )

        created_count = populate_session_questions(
            session=session,
            questions_data=llm_questions,
            raw_role=raw_role,
            question_source=question_source,
            n=n_questions,
            difficulty=difficulty,
            job_role=job_role,
        )

    return session, created_count


def create_resume_jd_session(
    user,
    resume_obj: Optional[Resume] = None,
    job_description: str = "",
    difficulty: int = 3,
    n_questions: int = 5,
    resume_title: str = "",
    resume_file=None,
    pasted_resume: str = "",
) -> Tuple[Optional[InterviewSession], int]:
    """
    Creates an adaptive interview session tailored to the candidate's Resume and Job Description.
    Generates only the first main question (index=1, parent_answer=None) and stores
    max_main_questions=n_questions so subsequent questions adapt dynamically.
    """
    newly_created_resume = False
    # Resolve or create resume
    if not resume_obj:
        resume_obj = save_and_index_resume(
            user=user,
            title=resume_title,
            file_obj=resume_file,
            raw_text=pasted_resume,
        )
        if resume_obj:
            newly_created_resume = True

    if not resume_obj and not job_description:
        return None, 0

    clean_diff = max(1, min(5, int(difficulty or 3)))
    clean_max_main = max(1, min(30, int(n_questions or 5)))

    job_role = "Resume & JD Specific Match"
    if job_description:
        lines = [l.strip() for l in job_description.splitlines() if l.strip()]
        if lines:
            job_role = f"Job Match: {lines[0][:45]}"

    try:
        prev_questions = list(
            SessionQuestion.objects.filter(session__user=user, session__role="tech")
            .order_by("-id")
            .values_list("question__text", flat=True)
            .distinct()[:15]
        )

        rag_enabled = getattr(settings, "RAG_ENABLED", True) and _rag_available and (resume_obj is not None)
        question_source = "rag_resume" if rag_enabled else "llm"

        try:
            if rag_enabled and resume_obj:
                llm_questions = generate_resume_jd_rag_questions(
                    resume_obj=resume_obj,
                    job_description=job_description,
                    n=1,
                    difficulty=clean_diff,
                    previous_questions=prev_questions,
                )
            else:
                fallback_text = resume_obj.extracted_text if resume_obj else pasted_resume
                llm_questions = generate_resume_jd_questions_groq(
                    resume_text=fallback_text,
                    job_description=job_description,
                    n=1,
                    difficulty=clean_diff,
                    previous_questions=prev_questions,
                )
        except Exception as e:
            logger.exception("Resume/JD question generation error (rag=%s): %s", rag_enabled, e)
            llm_questions = []

        with transaction.atomic():
            session = InterviewSession.objects.create(
                user=user,
                resume=resume_obj,
                job_description=job_description,
                state="adaptive",
                max_main_questions=clean_max_main,
                total_questions=1,
                role="tech",
                job_role=job_role,
                difficulty=clean_diff,
                total_score=None,
                current_index=1,
            )

            created_count = populate_session_questions(
                session=session,
                questions_data=llm_questions,
                raw_role="tech",
                question_source=question_source,
                n=1,
                difficulty=clean_diff,
                job_role=job_role,
            )
    except Exception as exc:
        logger.exception("Failed to initialize resume/JD interview session: %s", exc)
        if newly_created_resume and resume_obj:
            logger.warning(
                "Cleaning up newly created Resume #%s due to session initialization failure.",
                resume_obj.id,
            )
            try:
                delete_candidate_resume(resume_obj)
            except Exception as cleanup_err:
                logger.exception(
                    "Failed to clean up resume #%s after session failure: %s",
                    resume_obj.id,
                    cleanup_err,
                )
        raise

    return session, created_count


def create_phase_practice_session(
    user,
    raw_role_param: str = "Full-Stack Developer",
    phase_num: str = "1",
    phase_title: str = "",
) -> Tuple[InterviewSession, int]:
    """Creates a targeted practice session for a specific roadmap phase."""
    job_role = f"{raw_role_param.replace('-', ' ').title()}"
    if phase_title:
        job_role += f" (Phase {phase_num}: {phase_title})"

    r_lower = raw_role_param.lower()
    raw_role = "tech"
    if any(k in r_lower for k in ["hr", "manager", "people"]):
        raw_role = "hr"
    elif any(k in r_lower for k in ["apt", "logic", "math"]):
        raw_role = "apt"

    return create_standard_session(
        user=user,
        raw_role=raw_role,
        job_role=job_role,
        difficulty=3,
        n_questions=5,
    )


def get_next_unprocessed_answer(session: InterviewSession) -> Optional[Answer]:
    """Finds the next unprocessed Answer placeholder and synchronizes session.current_index."""
    if session.completed:
        return None

    next_ans = session.answers.filter(processed=False).order_by("index").first()
    if next_ans:
        session.current_index = next_ans.index
        session.save(update_fields=["current_index"])
        return next_ans

    return None


def get_session_summary_data(session: InterviewSession) -> Dict:
    """
    Computes aggregate metrics, backfills expected answers, generates session suggestions,
    and formats resume grounding summaries.
    """
    answers = session.answers.select_related("question").all().order_by("index")
    scores = [a.score for a in answers if a.score is not None]
    avg = (sum(scores) / len(scores)) if scores else None
    session.total_score = avg
    session.save(update_fields=["total_score"])

    # Backfill expected answers for unanswered questions
    for a in answers:
        is_unanswered = (
            (not a.answer_text)
            or (a.answer_text.strip() in ["", "[Skipped]", "[Voice answer could not be transcribed]", "No answer provided"])
            or (a.score == 0)
        )
        a.is_unanswered = is_unanswered
        if a.question and not a.expected_answer:
            try:
                keywords_list = [k.strip() for k in a.question.keywords.split(",")] if a.question.keywords else []
                exp = generate_expected_answer(a.question.text, session.role, keywords_list)
                a.expected_answer = exp
                a.save(update_fields=["expected_answer"])
            except Exception:
                pass

    total_q = answers.count()
    attempted_answers = answers.exclude(answer_text__in=["[Skipped]", "", "[Voice answer could not be transcribed]"])
    attempted_count = attempted_answers.count()
    completion_rate = int((attempted_count / total_q) * 100) if total_q else 0

    attempted_scores = [a.score for a in attempted_answers if a.score is not None]
    content_quality_score = (sum(attempted_scores) / len(attempted_scores)) if attempted_scores else 0

    duration = 0
    if session.started_at and getattr(session, "completed_at", None):
        duration = int((session.completed_at - session.started_at).total_seconds() / 60)

    # Strengths / improvements heuristics
    strengths: List[str] = []
    improvements: List[str] = []
    for a in answers:
        fb = (a.feedback or "").lower()
        snippet = (
            a.question.text[:70] + ("..." if len(a.question.text) > 70 else "")
            if a.question
            else f"Question #{a.index}"
        )
        if fb:
            if "good" in fb or "excellent" in fb or "well" in fb:
                strengths.append(f"Strong answer to: {snippet}")
            if "improv" in fb or "better" in fb or "need" in fb:
                improvements.append(f"Could improve: {snippet}")

    strengths = list(dict.fromkeys(strengths))[:3]
    improvements = list(dict.fromkeys(improvements))[:5]

    # Suggestions payload
    answer_payload = [
        {
            "question_text": a.question.text if a.question else "",
            "answer_text": a.answer_text or "",
            "score": a.score if a.score is not None else 0,
            "feedback": a.feedback or "",
        }
        for a in answers
    ]

    from django.core.cache import cache

    suggestions_cache_key = f"session_suggestions:{session.id}:{len(answers)}"
    suggestions = getattr(session, "suggestions_json", None) or cache.get(suggestions_cache_key)
    if not suggestions:
        try:
            suggestions = generate_session_suggestions(session, answer_payload)
            if not isinstance(suggestions, dict):
                suggestions = None
        except Exception as e:
            logger.exception("Suggestion generation failed: %s", e)
            suggestions = None

    if suggestions:
        try:
            cache.set(suggestions_cache_key, suggestions, timeout=60 * 60 * 24)
        except Exception:
            pass
        if hasattr(session, "suggestions_json"):
            try:
                with transaction.atomic():
                    session.suggestions_json = suggestions
                    session.save(update_fields=["suggestions_json"])
            except Exception:
                pass

    if not suggestions:
        suggestions = {
            "strengths": strengths or ["Clear answers to some questions."],
            "improvements": improvements or ["Work on structuring answers and giving concrete examples."],
            "overall_tip": "Practice concise explanations, and focus on weaker areas identified above.",
            "resources": ["Review domain fundamentals", "Practice mock interviews", "Study common patterns"],
        }

    # Resume grounding summary
    resume_summary = None
    if session.resume:
        grounded_answers = [a for a in answers if a.resume_grounding]
        if grounded_answers:
            consistency_scores = [
                a.resume_grounding.get("consistency_score", 0)
                for a in grounded_answers
                if isinstance(a.resume_grounding, dict) and "consistency_score" in a.resume_grounding
            ]
            avg_consistency = (sum(consistency_scores) / len(consistency_scores)) if consistency_scores else 0
            consistency_pct = int((avg_consistency / 20) * 100)

            all_supported: List[str] = []
            all_contradictions: List[str] = []
            all_missed: List[str] = []
            for a in grounded_answers:
                rg = a.resume_grounding or {}
                all_supported.extend(rg.get("supported_claims", []))
                all_contradictions.extend(rg.get("contradictions", []))
                all_missed.extend(rg.get("missed_resume_points", []))

            resume_summary = {
                "resume_title": session.resume.title,
                "avg_consistency_score": round(avg_consistency, 1),
                "consistency_pct": consistency_pct,
                "supported_count": len(all_supported),
                "contradictions_count": len(all_contradictions),
                "missed_count": len(all_missed),
            }

    # Video summary and feedback
    video_summary = None
    video_ai_feedback = None
    if session.video_stats_json:
        video_summary = compute_video_confidence(session.video_stats_json)
    if session.video_feedback_json:
        video_ai_feedback = session.video_feedback_json

    return {
        "session": session,
        "answers": answers,
        "avg": round(avg, 2) if avg is not None else None,
        "content_quality_score": round(content_quality_score, 1),
        "completion_rate": completion_rate,
        "duration": duration,
        "strengths": suggestions.get("strengths", strengths),
        "improvements": suggestions.get("improvements", improvements),
        "overall_tip": suggestions.get("overall_tip", ""),
        "resources": suggestions.get("resources", []),
        "resume_summary": resume_summary,
        "video_summary": video_summary,
        "video_ai_feedback": video_ai_feedback,
    }
