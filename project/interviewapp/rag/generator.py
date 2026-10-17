"""
LLM generation module for the RAG pipeline.

Constructs grounded prompts with retrieved context chunks, invokes the Groq chat API,
extracts structured JSON arrays, and validates question structures.
"""

import logging
from typing import Dict, List, Optional

from ..qgen_groq import (
    _call_groq_chat,
    _extract_json_array_from_text,
    _validate_question_obj,
)
from .prompt_templates import build_rag_prompt
from .retriever import RetrievalResult

logger = logging.getLogger(__name__)


def generate_from_context(
    role: str,
    job_role: str,
    n: int,
    difficulty: int,
    retrieval_result: RetrievalResult,
    previous_questions: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> List[Dict]:
    """
    Generates interview questions grounded in retrieved context via Groq LLM.

    Builds a structured prompt using retrieved context chunks, calls Groq chat,
    parses the JSON response array, and validates each question object.

    Args:
        role: Interview round type (e.g., 'technical', 'hr').
        job_role: Job title target.
        n: Number of questions requested.
        difficulty: Difficulty integer (1 to 5).
        retrieval_result: RetrievalResult containing relevant context chunks.
        previous_questions: List of previous question strings to avoid.
        model: Optional Groq model identifier override.

    Returns:
        List of validated question dictionaries matching the format:
        [{'text': str, 'keywords': str, 'difficulty': int, 'type': str}]
    """
    if not retrieval_result or not retrieval_result.has_context or not retrieval_result.chunks:
        logger.warning("generate_from_context called without valid retrieval context; returning empty list")
        return []

    try:
        prompt = build_rag_prompt(
            role=role,
            job_role=job_role,
            n=n,
            difficulty=difficulty,
            context_chunks=retrieval_result.chunks,
            previous_questions=previous_questions,
        )

        logger.info(
            "Invoking Groq chat for RAG generation (role='%s', job_role='%s', n=%d, diff=%d, chunks=%d)",
            role,
            job_role,
            n,
            difficulty,
            len(retrieval_result.chunks),
        )

        # Use temperature=0.7 matching existing qgen_groq question generation variety
        raw_response = _call_groq_chat(prompt=prompt, model=model, temperature=0.7)

        if not raw_response or not raw_response.strip():
            logger.error("Groq chat returned empty response for RAG question generation")
            return []

        parsed_items = _extract_json_array_from_text(raw_response)

        validated_questions: List[Dict] = []
        for item in parsed_items:
            valid_q = _validate_question_obj(item)
            if valid_q:
                validated_questions.append(valid_q)
            else:
                logger.debug("Discarding invalid question object from LLM output: %s", item)

        logger.info(
            "Successfully generated and validated %d questions from RAG context (requested %d)",
            len(validated_questions),
            n,
        )
        return validated_questions

    except Exception as exc:
        logger.exception("Failed to generate questions from context: %s", exc)
        return []
