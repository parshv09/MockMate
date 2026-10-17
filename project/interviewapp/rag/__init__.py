"""
RAG (Retrieval-Augmented Generation) package for interview question generation.

This module provides document loading, splitting, vector indexing, retrieval,
and grounded question generation based on domain-specific knowledge bases.
"""

from .pipeline import generate_questions_with_rag

__all__ = ['generate_questions_with_rag']
