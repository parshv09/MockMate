"""
Deterministic skill-gap analyzer and concurrency-safe persistence service
for the Dynamic Learning Roadmap feature.
"""

from collections import defaultdict
import logging
import re
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

_STOPWORDS_AND_VERBS = {
    "a", "an", "the", "and", "or", "but", "in", "on", "at", "to", "for", "of",
    "with", "by", "from", "as", "is", "are", "was", "were", "be", "been", "being",
    "explain", "describe", "discuss", "define", "compare", "contrast", "difference",
    "between", "how", "what", "why", "when", "where", "which", "who", "whom",
    "whose", "would", "could", "should", "can", "will", "do", "does", "did",
    "using", "use", "used", "real", "life", "real-life", "example", "examples",
    "issue", "issues", "problem", "problems", "question", "questions", "concept",
    "concepts", "topic", "topics", "troubleshoot", "troubleshooting", "implement",
    "implementation", "overview", "basics", "fundamentals", "introduction",
    "general", "related", "about", "into", "over", "under", "through", "etc",
    "none", "null", "na", "n/a", "variant", "tell", "me", "your", "you", "they",
    "their", "this", "that", "these", "those", "have", "has", "had",
}

_CONCEPT_SYNONYMS = {
    "postgres": "PostgreSQL",
    "postgresql": "PostgreSQL",
    "js": "JavaScript",
    "javascript": "JavaScript",
    "ts": "TypeScript",
    "typescript": "TypeScript",
    "rest api": "REST APIs",
    "rest apis": "REST APIs",
    "rest": "REST APIs",
    "restful": "REST APIs",
    "restful api": "REST APIs",
    "orm": "Django ORM",
    "django orm": "Django ORM",
    "db indexing": "Database Indexing",
    "database indexing": "Database Indexing",
    "indexing": "Database Indexing",
    "index": "Database Indexing",
    "indexes": "Database Indexing",
    "cache": "Caching",
    "caching": "Caching",
    "redis": "Redis Caching",
    "redis caching": "Redis Caching",
    "async": "Asynchronous Programming",
    "asyncio": "Asynchronous Programming",
    "asynchronous programming": "Asynchronous Programming",
    "docker": "Docker",
    "docker container": "Docker",
    "docker containers": "Docker",
    "containers": "Docker",
    "auth": "Authentication",
    "authentication": "Authentication",
    "authz": "Authorization",
    "authorization": "Authorization",
    "sql": "SQL",
    "sql queries": "SQL",
    "ci/cd": "CI/CD",
    "cicd": "CI/CD",
    "k8s": "Kubernetes",
    "kubernetes": "Kubernetes",
    "http": "HTTP",
    "https": "HTTP",
    "debug": "Debugging",
    "debugging": "Debugging",
    "graphql": "GraphQL",
    "microservices": "Microservices",
    "microservice": "Microservices",
    "system design": "System Design",
    "load balancing": "Load Balancing",
    "rate limiting": "Rate Limiting",
    "unit testing": "Unit Testing",
    "react": "React",
    "react hooks": "React Hooks",
    "django": "Django",
    "python": "Python",
    "git": "Git",
    "websockets": "WebSockets",
    "websocket": "WebSockets",
    "concurrency": "Concurrency",
    "multithreading": "Concurrency",
    "encryption": "Encryption",
    "hashing": "Hashing",
    "sharding": "Database Sharding",
    "database sharding": "Database Sharding",
    "replication": "Database Replication",
    "acid": "ACID Transactions",
    "transactions": "Database Transactions",
    "cap theorem": "CAP Theorem",
    "design patterns": "Design Patterns",
    "dependency injection": "Dependency Injection",
    "memory management": "Memory Management",
    "garbage collection": "Garbage Collection",
    "query optimization": "Query Optimization",
    "distributed systems": "Distributed Systems",
    "message queues": "Message Queues",
    "jwt": "JWT Authentication",
    "oauth": "OAuth",
}

# Ordered longest-first so multiword technical concepts match before single words.
_KNOWN_CONCEPT_PATTERNS: List[Tuple[re.Pattern, str]] = [
    (
        re.compile(rf"\b{re.escape(alias)}\b", re.IGNORECASE),
        canonical,
    )
    for alias, canonical in sorted(
        _CONCEPT_SYNONYMS.items(),
        key=lambda item: len(item[0]),
        reverse=True,
    )
]


class RoadmapError(ValueError):
    """Base exception for learning roadmap operations."""


class RoadmapSessionIncompleteError(RoadmapError):
    """Raised when requesting a learning roadmap for an uncompleted session."""


class RoadmapGenerationInProgressError(RuntimeError):
    """Raised when another request is actively generating the session roadmap."""


def is_valid_concept_token(raw_token: str) -> bool:
    """
    Validates whether a candidate concept token is a meaningful technical concept
    rather than a stop word, generic question verb, single-letter token, or fragment.
    """
    cleaned = " ".join((raw_token or "").strip().split())
    if not cleaned:
        return False

    # Reject single-letter concepts and tokens with fewer than 2 alphanumeric chars
    alnum_chars = [ch for ch in cleaned if ch.isalnum()]
    if len(alnum_chars) < 2:
        return False

    lowered = cleaned.lower()
    if lowered in _STOPWORDS_AND_VERBS:
        return False

    words = [w.strip(".,;:!?()[]{}\"'") for w in lowered.split()]
    words = [w for w in words if w]
    if not words:
        return False

    # Reject if every word in the token is a stopword/generic verb
    if all(w in _STOPWORDS_AND_VERBS or len(w) < 2 for w in words):
        return False

    # Reject overly long sentence-like fragments (> 5 words)
    if len(words) > 5:
        return False

    return True


def _normalize_concept_name(raw_token: str) -> str:
    cleaned = " ".join((raw_token or "").strip().strip(".,;:!?()[]{}\"'").split())
    if not is_valid_concept_token(cleaned):
        return ""
    lowered = cleaned.lower()
    if lowered in _CONCEPT_SYNONYMS:
        return _CONCEPT_SYNONYMS[lowered]
    if len(cleaned) <= 4 and cleaned.isupper():
        return cleaned
    return cleaned.title()


def _derive_concepts_from_text(text: str) -> List[str]:
    """
    Derives meaningful technical concepts from full question/feedback context
    when explicit keywords are missing or invalid. Never slices arbitrary prefixes.
    """
    normalized_text = " ".join((text or "").split())
    if not normalized_text:
        return []

    found: List[str] = []
    for pattern, canonical in _KNOWN_CONCEPT_PATTERNS:
        if pattern.search(normalized_text) and canonical not in found:
            found.append(canonical)
            if len(found) >= 4:
                return found

    # Secondary pass: extract uppercase acronyms (e.g. CORS, DNS, TCP)
    for token in re.findall(r"\b[A-Z]{2,6}\b", normalized_text):
        norm = _normalize_concept_name(token)
        if norm and norm not in found:
            found.append(norm)
            if len(found) >= 4:
                return found

    return found


def _extract_concepts_from_answer(ans: Answer) -> List[str]:
    """
    Extracts validated, deduplicated technical concepts from `question.keywords`
    (primary) or derives them from the full question context. Falls back to
    `["Unclassified"]` when no reliable technical concept can be determined.
    """
    q = getattr(ans, "question", None)
    if not q:
        return ["Unclassified"]

    raw_kw = (getattr(q, "keywords", "") or "").strip()
    concepts: List[str] = []
    if raw_kw:
        for part in raw_kw.split(","):
            norm = _normalize_concept_name(part)
            if norm and norm not in concepts:
                concepts.append(norm)

    if not concepts:
        context_text = " ".join(
            part for part in [getattr(q, "text", "") or "", getattr(q, "expected_answer", "") or ""] if part
        )
        concepts = _derive_concepts_from_text(context_text)

    if not concepts:
        return ["Unclassified"]

    return concepts[:4]


def _compute_cluster_score(evaluated: List[Answer]) -> float:
    """
    Authoritative cluster-level score calculation across a main answer and its
    follow-ups. Explicit skips without a numeric score count as 0.0.
    """
    scores: List[float] = []
    for item in evaluated:
        if item.score is not None:
            scores.append(float(item.score))
        elif is_skipped_answer(item):
            scores.append(0.0)
    if not scores:
        return 0.0
    return round(sum(scores) / len(scores), 1)


def _compute_concept_avg_score(clusters: List[Dict]) -> float:
    """
    Authoritative concept-level average score across interaction clusters.
    Each main+follow-up cluster contributes once so follow-ups refine rather
    than inflate evidence.
    """
    if not clusters:
        return 0.0
    return round(sum(c["cluster_score"] for c in clusters) / len(clusters), 1)


def _format_score_pct(score: float) -> str:
    """Formats a 1-decimal score consistently for both descriptions and footers."""
    rounded = round(float(score), 1)
    if rounded.is_integer():
        return f"{int(rounded)}%"
    return f"{rounded:.1f}%"


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

        cluster_score = _compute_cluster_score(evaluated)
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
            raw_tips = item.improvement_tips
            tip_items = [raw_tips] if isinstance(raw_tips, str) else (raw_tips or [])
            for t in tip_items:
                if str(t).strip():
                    tips.append(str(t).strip())

        q_text = " ".join((getattr(main_ans.question, "text", "") or "").split())

        clusters.append(
            {
                "main_answer": main_ans,
                "follow_ups": fu_list,
                "cluster_score": cluster_score,
                "any_skipped": any_skipped,
                "all_skipped": all_skipped,
                "had_followup": len(fu_list) > 0,
                "difficulty": getattr(main_ans.question, "difficulty", None) or 3,
                "concepts": _extract_concepts_from_answer(main_ans),
                "question_context": q_text[:140],
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
        avg_score = _compute_concept_avg_score(cl_list)
        avg_score_str = _format_score_pct(avg_score)
        attempt_count = len(cl_list)
        skip_count = sum(1 for c in cl_list if c["any_skipped"])
        followup_count = sum(1 for c in cl_list if c["had_followup"])

        all_contradictions: List[str] = []
        all_missed: List[str] = []
        all_tips: List[str] = []
        question_contexts: List[str] = []
        for c in cl_list:
            all_contradictions.extend(c["contradictions"])
            all_missed.extend(c["missed_resume_points"])
            all_tips.extend(c["improvement_tips"])
            if c.get("question_context"):
                question_contexts.append(c["question_context"])

        all_contradictions = list(dict.fromkeys(all_contradictions))
        all_missed = list(dict.fromkeys(all_missed))
        all_tips = list(dict.fromkeys(all_tips))
        question_contexts = list(dict.fromkeys(question_contexts))[:2]

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
                f"Average score of {avg_score_str} across {attempt_count} interaction(s) on {concept}."
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

        classification = (
            "demonstrated_weakness"
            if (skip_count > 0 or all_contradictions or avg_score < 75)
            else "optional_advanced_learning"
        )

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
                "classification": classification,
                "avg_score": avg_score,
                "attempt_count": attempt_count,
                "skip_count": skip_count,
                "followup_count": followup_count,
                "scope": scope_note,
                "question_context": question_contexts,
                "demonstrated_weaknesses": demonstrated_weaknesses,
                "improvement_opportunities": improvement_opportunities,
            }
        )

    skill_gaps.sort(
        key=lambda g: (
            1 if g["concept"] == "Unclassified" else 0,
            _PRIORITY_RANK.get(g["priority"], 9),
            g["avg_score"],
            g["concept"],
        )
    )

    has_classified_gaps = any(g["concept"] != "Unclassified" for g in skill_gaps)
    if not skill_gaps:
        evidence_status = "strong_no_gaps"
    elif not has_classified_gaps:
        evidence_status = "unclassified"
    else:
        evidence_status = "sufficient"

    return {
        "has_sufficient_evidence": True,
        "evidence_status": evidence_status,
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

        existing_for_regen = get_learning_roadmap(session) if force_regenerate else None
        gap_analysis = analyze_session_skill_gaps(session)
        roadmap_payload = generate_learning_roadmap_groq(
            skill_gaps_summary=gap_analysis,
            role=session.role,
            job_role=session.job_role,
            difficulty=session.difficulty,
            raise_on_failure=bool(force_regenerate and existing_for_regen is not None),
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

