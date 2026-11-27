"""
Deterministic skill-gap analyzer and concurrency-safe persistence service
for the Dynamic Learning Roadmap feature.
"""

from collections import defaultdict
import logging
import threading
import uuid
from typing import Dict, List, Optional, Tuple

from django.core.cache import cache
from django.db import transaction

from ..models import Answer, InterviewSession, LearningRoadmap
from .adaptive_service import is_skipped_answer

logger = logging.getLogger(__name__)

_LOCAL_LOCK_GUARD = threading.Lock()
_ACTIVE_LOCAL_LOCKS = set()

_PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}

_CONCEPT_SYNONYMS = {
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "rest api": "REST APIs",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "orm": "Django ORM",
    "django orm": "Django ORM",
    "db indexing": "Database Indexing",
    "indexing": "Database Indexing",
    "index": "Database Indexing",
    "indexes": "Database Indexing",
    "cache": "Caching",
    "caching": "Caching",
    "redis": "Redis Caching",
    "async": "Asynchronous Programming",
    "asyncio": "Asynchronous Programming",
}


class RoadmapError(ValueError):
    """Base exception for learning roadmap operations."""


class RoadmapSessionIncompleteError(RoadmapError):
    """Raised when requesting a learning roadmap for an uncompleted session."""


class RoadmapGenerationInProgressError(RuntimeError):
    """Raised when another request is actively generating the session roadmap."""


def _normalize_concept_name(raw_token: str) -> str:
    cleaned = " ".join((raw_token or "").strip().split())
    if not cleaned:
        return ""
    lowered = cleaned.lower()
    if lowered in _CONCEPT_SYNONYMS:
        return _CONCEPT_SYNONYMS[lowered]
    if len(cleaned) <= 4 and cleaned.isupper():
        return cleaned
    return cleaned.title()


def _extract_concepts_from_answer(ans: Answer) -> List[str]:
    """
    Extracts normalized concepts from `question.keywords` (primary) or
    falls back to a concise concept derived from `question.text`.
    """
    q = getattr(ans, "question", None)
    if not q:
        return []

    raw_kw = (getattr(q, "keywords", "") or "").strip()
    concepts: List[str] = []
    if raw_kw:
        for part in raw_kw.split(","):
            norm = _normalize_concept_name(part)
            if norm and norm not in concepts:
                concepts.append(norm)

    if not concepts:
        q_text = " ".join((getattr(q, "text", "") or "").split())
        if q_text:
            snippet = q_text[:60].rstrip(" ?.,;:")
            concepts.append(snippet)

    return concepts[:4]


def _group_interaction_clusters(answers: List[Answer]) -> List[Dict]:
    """
    Groups main answers with their optional follow-up so follow-up answers are not
    counted as entirely independent subject evidence.
    """
    by_id = {a.id: a for a in answers}
    followups_by_parent: Dict[int, List[Answer]] = defaultdict(list)
    main_answers: List[Answer] = []

    for a in answers:
        if a.parent_answer_id and a.parent_answer_id in by_id:
            followups_by_parent[a.parent_answer_id].append(a)
        else:
            main_answers.append(a)

    clusters: List[Dict] = []
    for main_ans in main_answers:
        fu_list = followups_by_parent.get(main_ans.id, [])
        all_in_cluster = [main_ans] + fu_list

        # Filter to evaluated/processed interactions (or explicit skips)
        evaluated = [
            item for item in all_in_cluster
            if item.processed or item.score is not None or is_skipped_answer(item)
        ]
        if not evaluated:
            continue

        scores = [float(item.score) for item in evaluated if item.score is not None]
        # Combined cluster score: average across main + follow-up so follow-up refines main score
        cluster_score = (sum(scores) / len(scores)) if scores else 0.0
        any_skipped = any(is_skipped_answer(item) for item in evaluated)
        all_skipped = all(is_skipped_answer(item) for item in evaluated)

        contradictions: List[str] = []
        missed_points: List[str] = []
        tips: List[str] = []
        for item in evaluated:
            rg = item.resume_grounding if isinstance(item.resume_grounding, dict) else {}
            for c in rg.get("contradictions") or []:
                if str(c).strip():
                    contradictions.append(str(c).strip())
            for mp in rg.get("missed_resume_points") or []:
                if str(mp).strip():
                    missed_points.append(str(mp).strip())
            for t in item.improvement_tips or []:
                if str(t).strip():
                    tips.append(str(t).strip())

        clusters.append(
            {
                "main_answer": main_ans,
                "follow_ups": fu_list,
                "cluster_score": round(cluster_score, 1),
                "any_skipped": any_skipped,
                "all_skipped": all_skipped,
                "had_followup": len(fu_list) > 0,
                "difficulty": getattr(main_ans.question, "difficulty", None) or 3,
                "concepts": _extract_concepts_from_answer(main_ans),
                "contradictions": list(dict.fromkeys(contradictions)),
                "missed_resume_points": list(dict.fromkeys(missed_points)),
                "improvement_tips": list(dict.fromkeys(tips)),
            }
        )

    return clusters


def analyze_session_skill_gaps(session: InterviewSession) -> Dict:
    """
    Pure deterministic Python skill-gap and priority analyzer.
    Performs zero Groq calls and zero database writes.
    """
    answers = list(session.answers.select_related("question").order_by("index"))
    clusters = _group_interaction_clusters(answers)

    if not clusters:
        return {
            "has_sufficient_evidence": False,
            "evidence_status": "insufficient_evidence",
            "evaluated_interactions": 0,
            "skill_gaps": [],
        }

    concept_buckets: Dict[str, List[Dict]] = defaultdict(list)
    for cl in clusters:
        for concept in cl["concepts"]:
            concept_buckets[concept].append(cl)

    subject_label = (session.role or "general").upper()
    skill_gaps: List[Dict] = []

    for concept, cl_list in concept_buckets.items():
        avg_score = sum(c["cluster_score"] for c in cl_list) / len(cl_list)
        attempt_count = len(cl_list)
        skip_count = sum(1 for c in cl_list if c["any_skipped"])
        followup_count = sum(1 for c in cl_list if c["had_followup"])

        all_contradictions: List[str] = []
        all_missed: List[str] = []
        all_tips: List[str] = []
        for c in cl_list:
            all_contradictions.extend(c["contradictions"])
            all_missed.extend(c["missed_resume_points"])
            all_tips.extend(c["improvement_tips"])

        all_contradictions = list(dict.fromkeys(all_contradictions))
        all_missed = list(dict.fromkeys(all_missed))
        all_tips = list(dict.fromkeys(all_tips))

        demonstrated_weaknesses: List[str] = []
        improvement_opportunities: List[str] = []

        if skip_count > 0:
            demonstrated_weaknesses.append(f"Skipped {skip_count} question(s) involving {concept}.")
        if all_contradictions:
            demonstrated_weaknesses.append(
                f"Resume discrepancy noted: {all_contradictions[0]}"
            )
        if avg_score < 75:
            demonstrated_weaknesses.append(
                f"Average score of {round(avg_score)}% across {attempt_count} interaction(s) on {concept}."
            )

        if all_missed:
            improvement_opportunities.append(
                f"Missed resume evidence: {', '.join(all_missed[:2])}."
            )
        if all_tips:
            improvement_opportunities.extend(all_tips[:2])

        # Priority classification rules
        is_repeated_weak = attempt_count >= 2 and avg_score < 65
        if skip_count > 0 or all_contradictions or avg_score < 50 or is_repeated_weak:
            priority = "High"
        elif avg_score < 75 or (followup_count > 0 and avg_score < 75) or len(improvement_opportunities) >= 2:
            priority = "Medium"
        elif improvement_opportunities:
            priority = "Low"
        else:
            # Strong performance with zero gaps or improvement signals -> skip inventing a weakness
            continue

        # Avoid branding an entire broad subject weak from one isolated answer
        scope_note = (
            "isolated_question"
            if attempt_count == 1
            else "multi_question_pattern"
        )

        skill_gaps.append(
            {
                "concept": concept,
                "subject": subject_label,
                "priority": priority,
                "avg_score": round(avg_score, 1),
                "attempt_count": attempt_count,
                "skip_count": skip_count,
                "followup_count": followup_count,
                "scope": scope_note,
                "demonstrated_weaknesses": demonstrated_weaknesses,
                "improvement_opportunities": improvement_opportunities,
            }
        )

    skill_gaps.sort(key=lambda g: (_PRIORITY_RANK.get(g["priority"], 9), g["avg_score"], g["concept"]))

    return {
        "has_sufficient_evidence": True,
        "evidence_status": "sufficient" if skill_gaps else "strong_no_gaps",
        "evaluated_interactions": len(clusters),
        "skill_gaps": skill_gaps[:8],
    }


def _acquire_generation_lock(session_id: int) -> str:
    token = uuid.uuid4().hex
    cache_key = f"learning_roadmap_gen_lock:{session_id}"
    with _LOCAL_LOCK_GUARD:
        if session_id in _ACTIVE_LOCAL_LOCKS:
            raise RoadmapGenerationInProgressError(
                "Learning roadmap generation is already in progress for this session."
            )
        added = cache.add(cache_key, token, timeout=120)
        if not added:
            raise RoadmapGenerationInProgressError(
                "Learning roadmap generation is already in progress for this session."
            )
        _ACTIVE_LOCAL_LOCKS.add(session_id)
    return token


def _release_generation_lock(session_id: int, token: str) -> None:
    cache_key = f"learning_roadmap_gen_lock:{session_id}"
    with _LOCAL_LOCK_GUARD:
        _ACTIVE_LOCAL_LOCKS.discard(session_id)
        try:
            if cache.get(cache_key) == token:
                cache.delete(cache_key)
        except Exception:
            pass


def get_learning_roadmap(session: InterviewSession) -> Optional[LearningRoadmap]:
    """Returns the persisted LearningRoadmap for a session, or None if not yet generated."""
    return LearningRoadmap.objects.filter(session=session).first()


def generate_learning_roadmap_for_session(
    session: InterviewSession,
    *,
    force_regenerate: bool = False,
) -> Tuple[LearningRoadmap, bool]:
    """
    Generates or retrieves the LearningRoadmap for a completed InterviewSession.
    Returns `(roadmap_obj, created_now)`.
    - Returns cached roadmap without calling Groq when `force_regenerate=False`.
    - Protects against simultaneous duplicate generation requests.
    - Runs Groq outside database transactions and preserves any prior roadmap on failure.
    """
    from ..qgen_groq import generate_learning_roadmap_groq

    if not session.completed:
        raise RoadmapSessionIncompleteError(
            "Learning roadmap can only be generated after the interview session is completed."
        )

    if not force_regenerate:
        existing = get_learning_roadmap(session)
        if existing is not None:
            return existing, False

    lock_token = _acquire_generation_lock(session.id)
    try:
        # Re-check inside lock for concurrent callers
        if not force_regenerate:
            existing = get_learning_roadmap(session)
            if existing is not None:
                return existing, False

        gap_analysis = analyze_session_skill_gaps(session)
        roadmap_payload = generate_learning_roadmap_groq(
            skill_gaps_summary=gap_analysis,
            role=session.role,
            job_role=session.job_role,
            difficulty=session.difficulty,
        )

        with transaction.atomic():
            roadmap_obj, created = LearningRoadmap.objects.update_or_create(
                session=session,
                defaults={
                    "skill_gaps_json": gap_analysis.get("skill_gaps", []),
                    "roadmap_json": roadmap_payload,
                },
            )
        return roadmap_obj, created
    finally:
        _release_generation_lock(session.id, lock_token)

