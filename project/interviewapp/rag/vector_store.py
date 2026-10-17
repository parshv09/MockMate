"""
Vector store module for the RAG pipeline.

Provides a persistent, thread-safe vector store with cosine distance querying,
metadata filtering, and atomic disk persistence. Compatible with ChromaDB and
robust against native C++ Windows runtime conflicts.
"""

import json
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
from django.conf import settings

logger = logging.getLogger(__name__)

_vector_store_instance: Optional["VectorStore"] = None
_vs_lock = threading.Lock()


class VectorStore:
    """
    Robust, persistent vector store using normalized cosine similarity.

    Persists embeddings and metadata atomically to disk in the configured index
    directory. Thread-safe, cross-platform, and free from external C++ DLL conflicts.
    """

    def __init__(
        self,
        persist_dir: Optional[Union[str, Path]] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initializes VectorStore with storage directory and collection name.

        Args:
            persist_dir: Directory path to persist vectors and metadata.
            collection_name: Logical collection identifier.
        """
        if not persist_dir:
            persist_dir = getattr(settings, "RAG_INDEX_DIR", None)
        if not persist_dir:
            base_dir = getattr(settings, "BASE_DIR", Path.cwd())
            persist_dir = Path(base_dir) / "rag_index"

        self.persist_dir = Path(persist_dir)

        if not collection_name:
            collection_name = getattr(settings, "RAG_COLLECTION_NAME", "mockmate_interview_knowledge")

        self.collection_name: str = collection_name
        self._lock = threading.Lock()
        self._init_attempted = False
        self._available = False

        # In-memory index structures
        self._ids: List[str] = []
        self._documents: List[str] = []
        self._metadatas: List[Dict[str, Any]] = []
        self._embeddings: Optional[np.ndarray] = None  # Shape (N, D), float32 normalized

    @property
    def _meta_file(self) -> Path:
        return self.persist_dir / "store_metadata.json"

    @property
    def _vec_file(self) -> Path:
        return self.persist_dir / "store_vectors.npy"

    def _ensure_initialized(self) -> None:
        """Loads existing index from disk under thread lock."""
        if self._init_attempted:
            return

        with self._lock:
            if self._init_attempted:
                return

            self._init_attempted = True
            try:
                self.persist_dir.mkdir(parents=True, exist_ok=True)
                self._load_from_disk()
                self._available = True
                logger.info(
                    "Connected to vector store '%s' at %s (loaded %d documents)",
                    self.collection_name,
                    self.persist_dir,
                    len(self._ids),
                )
            except Exception as exc:
                logger.error("Failed to initialize vector store at %s: %s", self.persist_dir, exc)
                self._available = False

    def _load_from_disk(self) -> None:
        """Reads metadata JSON and vectors NPY files if present."""
        if self._meta_file.exists():
            try:
                with open(self._meta_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self._ids = data.get("ids", [])
                self._documents = data.get("documents", [])
                self._metadatas = data.get("metadatas", [])
            except Exception as exc:
                logger.warning("Could not read vector store metadata: %s", exc)
                self._ids, self._documents, self._metadatas = [], [], []

        if self._vec_file.exists() and len(self._ids) > 0:
            try:
                mat = np.load(str(self._vec_file))
                if mat.ndim == 2 and mat.shape[0] == len(self._ids):
                    self._embeddings = mat.astype(np.float32)
                else:
                    logger.warning("Vector dimensions mismatch on disk; resetting embeddings")
                    self._embeddings = None
            except Exception as exc:
                logger.warning("Could not load vectors.npy: %s", exc)
                self._embeddings = None
        else:
            self._embeddings = None

    def _save_to_disk(self) -> None:
        """Atomically saves index metadata and vectors to disk."""
        self.persist_dir.mkdir(parents=True, exist_ok=True)

        meta_temp = self.persist_dir / "store_metadata.tmp"
        with open(meta_temp, "w", encoding="utf-8") as f:
            json.dump(
                {
                    "collection": self.collection_name,
                    "ids": self._ids,
                    "documents": self._documents,
                    "metadatas": self._metadatas,
                },
                f,
                ensure_ascii=False,
                indent=2,
            )
        if meta_temp.exists():
            meta_temp.replace(self._meta_file)

        if self._embeddings is not None and len(self._embeddings) > 0:
            vec_temp = self.persist_dir / "store_vectors.tmp.npy"
            np.save(str(vec_temp), self._embeddings)
            if vec_temp.exists():
                vec_temp.replace(self._vec_file)

    def is_available(self) -> bool:
        """
        Checks whether the vector store is initialized and ready.

        Returns:
            True if ready, False otherwise.
        """
        self._ensure_initialized()
        return self._available

    def add_documents(
        self,
        ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """
        Upserts document chunks, embeddings, and metadata into the collection.

        Args:
            ids: List of unique chunk IDs.
            texts: List of chunk text strings.
            embeddings: List of embedding vectors.
            metadatas: List of chunk metadata dictionaries.
        """
        if not ids or not texts:
            logger.debug("add_documents called with empty payload, skipping")
            return

        self._ensure_initialized()
        if not self.is_available():
            logger.warning("VectorStore is unavailable; cannot add documents")
            return

        with self._lock:
            # Build fast lookup map of existing IDs
            id_to_idx = {chunk_id: idx for idx, chunk_id in enumerate(self._ids)}

            new_vecs = np.array(embeddings, dtype=np.float32)
            # Normalize new vectors for fast cosine similarity via dot product
            norms = np.linalg.norm(new_vecs, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            new_vecs = new_vecs / norms

            cur_vecs = list(self._embeddings) if self._embeddings is not None and len(self._embeddings) > 0 else []

            for i, chunk_id in enumerate(ids):
                clean_meta = {}
                for k, v in (metadatas[i] if i < len(metadatas) and metadatas[i] else {}).items():
                    if v is None:
                        clean_meta[k] = ""
                    elif isinstance(v, (str, int, float, bool)):
                        clean_meta[k] = v
                    else:
                        clean_meta[k] = str(v)

                text = texts[i]
                vec = new_vecs[i]

                if chunk_id in id_to_idx:
                    idx = id_to_idx[chunk_id]
                    self._documents[idx] = text
                    self._metadatas[idx] = clean_meta
                    if idx < len(cur_vecs):
                        cur_vecs[idx] = vec
                else:
                    self._ids.append(chunk_id)
                    self._documents.append(text)
                    self._metadatas.append(clean_meta)
                    cur_vecs.append(vec)
                    id_to_idx[chunk_id] = len(self._ids) - 1

            if cur_vecs:
                self._embeddings = np.array(cur_vecs, dtype=np.float32)

            self._save_to_disk()
            logger.info("Successfully indexed %d documents into '%s'", len(self._ids), self.collection_name)

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[dict] = None,
    ) -> List[dict]:
        """
        Queries the vector store for nearest neighbors to the given query embedding.

        Computes cosine distance = 1.0 - cosine_similarity.

        Args:
            query_embedding: Float vector of the search query.
            top_k: Maximum number of chunks to return. Defaults to 5.
            where_filter: Optional metadata filtering dictionary.

        Returns:
            List of dicts: [{'text': str, 'metadata': dict, 'distance': float, 'id': str}]
        """
        if not query_embedding:
            return []

        self._ensure_initialized()
        if not self.is_available() or self.count() == 0 or self._embeddings is None:
            return []

        q_vec = np.array(query_embedding, dtype=np.float32)
        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []
        q_vec = q_vec / q_norm

        with self._lock:
            # Dot product with pre-normalized vectors gives cosine similarity in [-1, 1]
            sims = np.dot(self._embeddings, q_vec)
            # Cosine distance = 1.0 - similarity (range: [0.0, 2.0])
            distances = np.clip(1.0 - sims, 0.0, 2.0)

            # Filter candidates by metadata if where_filter is present
            candidates = []
            for idx in range(len(self._ids)):
                if where_filter:
                    meta = self._metadatas[idx]
                    match = all(meta.get(k) == v for k, v in where_filter.items())
                    if not match:
                        continue
                candidates.append((distances[idx], idx))

            if not candidates:
                return []

            # Sort by lowest distance (highest similarity)
            candidates.sort(key=lambda x: x[0])
            effective_k = min(top_k, len(candidates))

            output: List[dict] = []
            for dist, idx in candidates[:effective_k]:
                output.append({
                    "text": self._documents[idx],
                    "metadata": self._metadatas[idx],
                    "distance": float(dist),
                    "id": self._ids[idx],
                })

            return output

    def count(self) -> int:
        """
        Returns the total number of documents indexed in the collection.

        Returns:
            Document count, or 0 if unavailable/empty.
        """
        self._ensure_initialized()
        return len(self._ids)

    def clear(self) -> None:
        """Deletes all indexed documents from the collection and resets storage."""
        self._ensure_initialized()
        with self._lock:
            self._ids = []
            self._documents = []
            self._metadatas = []
            self._embeddings = None
            if self._meta_file.exists():
                try:
                    self._meta_file.unlink()
                except OSError:
                    pass
            if self._vec_file.exists():
                try:
                    self._vec_file.unlink()
                except OSError:
                    pass
            logger.info("Successfully cleared vector store collection '%s'", self.collection_name)

    def delete_collection(self) -> None:
        """Removes the collection entirely."""
        self.clear()


def get_vector_store() -> VectorStore:
    """
    Returns the thread-safe singleton instance of VectorStore.

    Returns:
        VectorStore instance.
    """
    global _vector_store_instance
    if _vector_store_instance is None:
        with _vs_lock:
            if _vector_store_instance is None:
                _vector_store_instance = VectorStore()
    return _vector_store_instance
