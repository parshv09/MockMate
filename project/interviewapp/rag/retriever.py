"""
Retriever module for the RAG pipeline.

Constructs rich semantic search queries, retrieves relevant context chunks from the
vector store, applies similarity thresholds, deduplicates overlapping passages, and
caps total prompt context length.
"""

import difflib
import logging
from dataclasses import dataclass, field
from typing import List, Optional

from django.conf import settings

from .embeddings import get_embedding_model
from .vector_store import get_vector_store

logger = logging.getLogger(__name__)

MAX_CONTEXT_CHARACTERS = 4000
CHUNK_SIMILARITY_DEDUP_RATIO = 0.90


@dataclass
class RetrievalResult:
    """Encapsulates context chunks and query metadata retrieved from the vector store."""

    chunks: List[dict] = field(default_factory=list)
    query: str = ""
    has_context: bool = False


def build_retrieval_query(
    role: str,
    job_role: str,
    difficulty: int,
    category: str = "",
) -> str:
    """
    Constructs a natural language retrieval query from interview parameters.

    Maps difficulty integers to descriptive levels:
    - 1-2: 'beginner fundamentals'
    - 3: 'intermediate practical'
    - 4-5: 'advanced expert'

    Args:
        role: Interview category (e.g. 'technical', 'hr', 'behavioral', 'aptitude').
        job_role: Target job title (e.g. 'Python developer').
        difficulty: Difficulty integer from 1 to 5.
        category: Optional sub-topic category.

    Returns:
        Structured query string for vector embedding search.
    """
    try:
        diff_val = int(difficulty)
    except (ValueError, TypeError):
        diff_val = 3

    if diff_val <= 2:
        level_desc = "beginner fundamentals"
        level_focus = "core syntax, definitions, basic operations, and foundational concepts"
    elif diff_val <= 4:
        level_desc = "intermediate practical"
        level_focus = "OOP, data structures, frameworks, testing, and practical programming concepts"
    else:
        level_desc = "advanced expert"
        level_focus = "architecture, concurrency, scaling challenges, performance optimization, and trade-offs"

    role_clean = role.strip().lower() if role else "technical"
    job_role_clean = job_role.strip() if job_role else "Software Developer"
    category_clean = category.strip() if category else ""

    parts = [job_role_clean]
    if category_clean:
        parts.append(category_clean)
    parts.append(level_desc)

    if "tech" in role_clean:
        parts.append(f"technical interview questions covering {level_focus}")
    elif "hr" in role_clean:
        parts.append("HR interview questions covering career goals, teamwork, communication, and culture fit")
    elif "beh" in role_clean:
        parts.append("behavioral interview questions covering handling deadlines, problem solving under pressure, and conflict resolution")
    elif "apt" in role_clean:
        parts.append("aptitude reasoning questions covering logical analysis, data interpretation, and problem solving")
    else:
        parts.append(f"interview questions covering {level_focus}")

    query = " ".join(parts).strip()
    logger.debug("Constructed retrieval query: '%s'", query)
    return query


def _is_near_duplicate(candidate_text: str, accepted_chunks: List[dict], threshold: float = CHUNK_SIMILARITY_DEDUP_RATIO) -> bool:
    """Checks whether candidate text has >= threshold similarity to any already accepted chunk."""
    cand_norm = " ".join(candidate_text.lower().split())
    for chunk in accepted_chunks:
        acc_text = chunk.get("text", "")
        acc_norm = " ".join(acc_text.lower().split())
        ratio = difflib.SequenceMatcher(None, cand_norm, acc_norm).ratio()
        if ratio >= threshold:
            return True
    return False


def retrieve_context(
    role: str,
    job_role: str,
    difficulty: int,
    category: str = "",
    top_k: Optional[int] = None,
) -> RetrievalResult:
    """
    Retrieves and filters knowledge chunks for the target interview parameters.

    Applies similarity threshold from settings.RAG_SIMILARITY_THRESHOLD, removes
    duplicate chunks (>90% overlap), and limits total context to ~4000 characters.

    Args:
        role: Interview type (e.g. 'technical', 'hr').
        job_role: Target job title (e.g. 'Python developer').
        difficulty: Difficulty rating (1 to 5).
        category: Optional subtopic.
        top_k: Max chunks to retrieve. Defaults to settings.RAG_TOP_K or 5.

    Returns:
        RetrievalResult instance with retrieved chunks and status.
    """
    query = build_retrieval_query(role, job_role, difficulty, category)

    rag_enabled = getattr(settings, "RAG_ENABLED", False)
    if not rag_enabled:
        logger.info("RAG is disabled in settings; returning empty RetrievalResult")
        return RetrievalResult(chunks=[], query=query, has_context=False)

    if top_k is None:
        top_k = getattr(settings, "RAG_TOP_K", 5)

    try:
        top_k = max(1, int(top_k))
    except (ValueError, TypeError):
        top_k = 5

    similarity_threshold = getattr(settings, "RAG_SIMILARITY_THRESHOLD", 0.3)
    try:
        similarity_threshold = float(similarity_threshold)
    except (ValueError, TypeError):
        similarity_threshold = 0.3

    embed_model = get_embedding_model()
    if not embed_model.is_available():
        logger.warning("Embedding model is unavailable; retrieval skipped")
        return RetrievalResult(chunks=[], query=query, has_context=False)

    query_embedding = embed_model.embed_query(query)
    if not query_embedding:
        logger.warning("Failed to generate query embedding; retrieval skipped")
        return RetrievalResult(chunks=[], query=query, has_context=False)

    vector_store = get_vector_store()
    if not vector_store.is_available() or vector_store.count() == 0:
        logger.info("Vector store is empty or unavailable; returning empty RetrievalResult")
        return RetrievalResult(chunks=[], query=query, has_context=False)

    # Fetch extra candidates to account for threshold filtering and deduplication
    fetch_k = max(top_k * 2, 10)
    raw_results = vector_store.query(query_embedding=query_embedding, top_k=fetch_k)

    if not raw_results:
        logger.info("Vector store returned 0 raw results for query")
        return RetrievalResult(chunks=[], query=query, has_context=False)

    # Filter by similarity threshold: in cosine space, distance in [0, 2], similarity = 1 - distance
    accepted_chunks: List[dict] = []
    total_context_chars = 0

    for item in raw_results:
        distance = float(item.get("distance", 0.0))
        similarity = max(0.0, 1.0 - distance)

        if similarity < similarity_threshold:
            logger.debug("Filtered out chunk with similarity %.3f < %.3f", similarity, similarity_threshold)
            continue

        text = item.get("text", "").strip()
        if not text:
            continue

        # Check for near-identical chunks (>90% overlap)
        if _is_near_duplicate(text, accepted_chunks):
            logger.debug("Deduplicated near-identical chunk: %s", text[:40])
            continue

        # Context character limit safeguard (~4000 chars max)
        if total_context_chars + len(text) > MAX_CONTEXT_CHARACTERS and accepted_chunks:
            logger.debug("Context window threshold reached (%d chars); stopping accumulation", total_context_chars)
            break

        chunk_dict = {
            "text": text,
            "metadata": item.get("metadata", {}),
            "distance": distance,
        }
        accepted_chunks.append(chunk_dict)
        total_context_chars += len(text)

        if len(accepted_chunks) >= top_k:
            break

    has_context = len(accepted_chunks) > 0
    logger.info(
        "Retrieved %d valid context chunks for query '%s' (total %d chars, has_context=%s)",
        len(accepted_chunks),
        query[:60],
        total_context_chars,
        has_context,
    )

    return RetrievalResult(
        chunks=accepted_chunks,
        query=query,
        has_context=has_context,
    )
