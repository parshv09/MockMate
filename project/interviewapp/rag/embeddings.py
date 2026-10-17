"""
Embedding model wrapper module for the RAG pipeline.

Provides lazy-loaded, thread-safe sentence transformer embeddings for documents
and queries, with graceful fallbacks if dependencies are missing.
"""

import logging
import threading
from typing import List, Optional

from django.conf import settings

logger = logging.getLogger(__name__)

# Module-level singleton instance and lock
_model_instance: Optional["EmbeddingModel"] = None
_instance_lock = threading.Lock()


class EmbeddingModel:
    """
    Lazy-loaded embedding model using sentence-transformers.

    Thread-safe and fails gracefully if sentence_transformers is not installed
    or if the specified model weights cannot be loaded.
    """

    def __init__(self, model_name: Optional[str] = None):
        """
        Initializes the EmbeddingModel instance without loading weights immediately.

        Args:
            model_name: Hugging Face model identifier. If None, falls back to
                        settings.RAG_EMBEDDING_MODEL or 'sentence-transformers/all-MiniLM-L6-v2'.
        """
        if not model_name:
            model_name = getattr(settings, "RAG_EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

        self.model_name: str = model_name
        self._model = None
        self._load_lock = threading.Lock()
        self._load_attempted = False
        self._available = False

    def _ensure_loaded(self) -> None:
        """Loads the sentence transformer model lazily under thread lock."""
        if self._load_attempted:
            return

        with self._load_lock:
            if self._load_attempted:
                return

            self._load_attempted = True
            try:
                from sentence_transformers import SentenceTransformer

                logger.info("Loading sentence-transformers embedding model: %s", self.model_name)
                self._model = SentenceTransformer(self.model_name)
                self._available = True
                logger.info("Successfully loaded embedding model: %s", self.model_name)
            except ImportError as exc:
                logger.warning(
                    "sentence_transformers library is not installed (%s). "
                    "RAG embedding capabilities will be unavailable.",
                    exc,
                )
                self._model = None
                self._available = False
            except Exception as exc:
                logger.error("Failed to load embedding model '%s': %s", self.model_name, exc)
                self._model = None
                self._available = False

    def is_available(self) -> bool:
        """
        Checks whether the embedding model is successfully loaded and ready.

        Returns:
            True if model is available for encoding, False otherwise.
        """
        self._ensure_loaded()
        return self._available and self._model is not None

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Batch encodes a list of document strings into float vectors.

        Args:
            texts: List of document strings to embed.

        Returns:
            List of float vectors, or an empty list if model is unavailable or on error.
        """
        if not texts:
            return []

        if not self.is_available():
            logger.warning("Embedding model is unavailable; cannot embed texts")
            return []

        try:
            embeddings = self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            return embeddings.tolist()
        except Exception as exc:
            logger.error("Batch text embedding failed: %s", exc)
            return []

    def embed_query(self, query: str) -> List[float]:
        """
        Encodes a single query string into a float vector.

        Args:
            query: Natural language query string.

        Returns:
            Float vector list, or empty list if unavailable or on error.
        """
        if not query or not query.strip():
            return []

        if not self.is_available():
            logger.warning("Embedding model is unavailable; cannot embed query")
            return []

        try:
            embedding = self._model.encode(query.strip(), convert_to_numpy=True, show_progress_bar=False)
            return embedding.tolist()
        except Exception as exc:
            logger.error("Query embedding failed for '%s': %s", query[:50], exc)
            return []


def get_embedding_model() -> EmbeddingModel:
    """
    Returns the thread-safe singleton instance of EmbeddingModel.

    Returns:
        EmbeddingModel instance.
    """
    global _model_instance
    if _model_instance is None:
        with _instance_lock:
            if _model_instance is None:
                _model_instance = EmbeddingModel()
    return _model_instance
