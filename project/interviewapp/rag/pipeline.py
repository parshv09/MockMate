"""
Main pipeline module for Retrieval-Augmented Generation (RAG) question generation.

Coordinates context retrieval, grounded generation, validation, and transparent
fallback to standard Groq generation if RAG is disabled, index is unpopulated,
or retrieval/generation fails.
"""

import logging
import time
from typing import Dict, List, Optional

from django.conf import settings

from .generator import generate_from_context
from .retriever import retrieve_context
from .validators import validate_and_deduplicate

logger = logging.getLogger(__name__)


def generate_questions_with_rag(
    role: str,
    job_role: str,
    n: int = 5,
    difficulty: int = 3,
    previous_questions: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> List[Dict]:
    """
    Generates interview questions using the RAG pipeline with automatic fallback to non-RAG generation.

    Pipeline steps:
    1. Check settings.RAG_ENABLED; fall back if disabled.
    2. Retrieve relevant domain context from the vector store and measure retrieval latency.
    3. If context is retrieved, invoke Groq with grounded context and measure generation latency.
    4. Validate and deduplicate generated questions.
    5. If sufficient questions are produced, return them.
    6. If retrieval yields no context or generation fails/produces insufficient items,
       log fallback and call interviewapp.qgen_groq.generate_questions_groq.

    Args:
        role: Interview type ('technical', 'hr', 'behavioral', 'aptitude').
        job_role: Target job position (e.g. 'Python Backend Developer').
        n: Number of questions to produce. Defaults to 5.
        difficulty: Question difficulty (1 to 5). Defaults to 3.
        previous_questions: Optional list of question strings to avoid duplicating.
        model: Optional model identifier override for Groq.

    Returns:
        List of question dictionaries in the exact schema:
        [{'text': str, 'keywords': str, 'difficulty': int, 'type': str}]
    """
    rag_enabled = getattr(settings, "RAG_ENABLED", False)
    if not rag_enabled:
        logger.info("RAG is disabled in settings (RAG_ENABLED=False); falling back to non-RAG generation")
        from ..qgen_groq import generate_questions_groq

        return generate_questions_groq(
            role=role,
            job_role=job_role,
            n=n,
            difficulty=difficulty,
            previous_questions=previous_questions,
            model=model,
        )

    try:
        # Step 1: Retrieval Phase
        retrieval_start = time.perf_counter()
        retrieval_result = retrieve_context(
            role=role,
            job_role=job_role,
            difficulty=difficulty,
        )
        retrieval_duration = time.perf_counter() - retrieval_start
        logger.info(
            "RAG retrieval phase completed in %.3fs (has_context=%s, chunks_found=%d)",
            retrieval_duration,
            retrieval_result.has_context,
            len(retrieval_result.chunks),
        )

        # Step 2: Generation Phase if context is present
        if retrieval_result.has_context:
            generation_start = time.perf_counter()
            raw_questions = generate_from_context(
                role=role,
                job_role=job_role,
                n=n,
                difficulty=difficulty,
                retrieval_result=retrieval_result,
                previous_questions=previous_questions,
                model=model,
            )
            validated_questions = validate_and_deduplicate(
                questions=raw_questions,
                n=n,
                previous_questions=previous_questions,
            )
            generation_duration = time.perf_counter() - generation_start
            logger.info(
                "RAG generation phase completed in %.3fs (validated_count=%d, requested=%d)",
                generation_duration,
                len(validated_questions),
                n,
            )

            # If enough questions were successfully generated, return them
            if len(validated_questions) >= n:
                logger.info("RAG pipeline successfully generated %d questions", len(validated_questions[:n]))
                return validated_questions[:n]

            logger.warning(
                "RAG generation produced %d/%d questions. Falling back to non-RAG generation to ensure full batch.",
                len(validated_questions),
                n,
            )
        else:
            logger.info("RAG retrieval found no relevant context; falling back to non-RAG generation")

    except Exception as exc:
        logger.exception("Unexpected error in RAG pipeline execution: %s", exc)

    # Step 3: Fallback Phase
    logger.info("Falling back to non-RAG generation via generate_questions_groq")
    from ..qgen_groq import generate_questions_groq

    return generate_questions_groq(
        role=role,
        job_role=job_role,
        n=n,
        difficulty=difficulty,
        previous_questions=previous_questions,
        model=model,
    )
