"""
Validation and deduplication module for the RAG pipeline.

Ensures generated questions meet schema requirements, checks for semantic and hash-based
duplicates, filters questions too similar to previously asked ones, and trims to the target batch size.
"""

import difflib
import logging
from typing import Dict, List, Optional

from ..qgen_groq import signature_of_text

logger = logging.getLogger(__name__)

SIMILARITY_THRESHOLD_PREVIOUS = 0.80
SIMILARITY_THRESHOLD_INTERNAL = 0.85


def _is_similar_to_any(text: str, comparison_texts: List[str], threshold: float) -> bool:
    """
    Checks if normalized text has a SequenceMatcher similarity ratio exceeding threshold
    against any text in comparison_texts.

    Args:
        text: Target text to compare.
        comparison_texts: List of reference strings.
        threshold: Ratio threshold (0.0 to 1.0) above which text is deemed too similar.

    Returns:
        True if similar, False otherwise.
    """
    norm_text = " ".join(text.lower().split())
    for comp in comparison_texts:
        if not comp:
            continue
        norm_comp = " ".join(str(comp).lower().split())
        ratio = difflib.SequenceMatcher(None, norm_text, norm_comp).ratio()
        if ratio > threshold:
            return True
    return False


def validate_and_deduplicate(
    questions: List[Dict],
    n: int,
    previous_questions: Optional[List[str]] = None,
) -> List[Dict]:
    """
    Validates question dictionaries, removes duplicates, and trims to size n.

    - Ensures fields 'text', 'keywords', 'difficulty', and 'type' are well-formed.
    - Uses SHA-256 signature_of_text for exact normalization deduplication.
    - Filters out questions with >80% similarity to previous_questions.
    - Filters out questions with >85% internal mutual similarity.
    - Trims to exactly n questions.

    Args:
        questions: Raw list of question dictionaries.
        n: Target number of questions to return.
        previous_questions: Optional list of previously asked questions to avoid.

    Returns:
        Cleaned, deduplicated list of questions (length <= n).
    """
    if not questions:
        return []

    target_n = max(1, n)
    clean_previous: List[str] = [str(q).strip() for q in (previous_questions or []) if str(q).strip()]

    seen_signatures = set()
    accepted_questions: List[Dict] = []
    accepted_texts: List[str] = []

    for q in questions:
        if not isinstance(q, dict):
            continue

        raw_text = q.get("text")
        if not raw_text or not isinstance(raw_text, str) or not raw_text.strip():
            continue

        text_clean = raw_text.strip()

        # Check hash signature deduplication
        sig = signature_of_text(text_clean)
        if sig in seen_signatures:
            logger.debug("Discarding duplicate question by hash signature: %s", text_clean[:50])
            continue

        # Check similarity against previously asked questions (>80%)
        if _is_similar_to_any(text_clean, clean_previous, SIMILARITY_THRESHOLD_PREVIOUS):
            logger.debug("Discarding question too similar to previous questions (>80%%): %s", text_clean[:50])
            continue

        # Check internal similarity against already accepted questions in this batch (>85%)
        if _is_similar_to_any(text_clean, accepted_texts, SIMILARITY_THRESHOLD_INTERNAL):
            logger.debug("Discarding internally redundant question (>85%%): %s", text_clean[:50])
            continue

        # Format and validate fields
        raw_keywords = q.get("keywords", "")
        if isinstance(raw_keywords, list):
            keywords_clean = ",".join(str(k).strip() for k in raw_keywords if str(k).strip())
        else:
            keywords_clean = str(raw_keywords).strip()

        try:
            diff_clean = int(q.get("difficulty", 3))
            diff_clean = max(1, min(5, diff_clean))
        except (ValueError, TypeError):
            diff_clean = 3

        type_raw = str(q.get("type", "reasoning")).strip().lower()
        type_clean = type_raw if type_raw in ("math", "reasoning") else "reasoning"

        clean_item = {
            "text": text_clean,
            "keywords": keywords_clean,
            "difficulty": diff_clean,
            "type": type_clean,
        }

        seen_signatures.add(sig)
        accepted_questions.append(clean_item)
        accepted_texts.append(text_clean)

        if len(accepted_questions) >= target_n:
            break

    logger.info("Validated and deduplicated %d questions down to %d", len(questions), len(accepted_questions))
    return accepted_questions[:target_n]
