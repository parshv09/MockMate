"""
RAG (Retrieval-Augmented Generation) package for interview question generation.

This module provides document loading, splitting, vector indexing, retrieval,
and grounded question generation based on domain-specific knowledge bases.
"""

from .pipeline import generate_questions_with_rag
from .resume_rag import generate_resume_jd_rag_questions, index_resume

__all__ = [
    'generate_questions_with_rag',
    'generate_resume_jd_rag_questions',
    'index_resume',
]
