"""
Vector store module for the RAG pipeline.

Wraps ChromaDB with persistent disk storage, provides upsert, semantic query,
collection management, and safe handling of missing dependencies and empty indexes.
"""

import logging
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from django.conf import settings

logger = logging.getLogger(__name__)

# Module-level singleton instance and lock
_vector_store_instance: Optional["VectorStore"] = None
_vs_lock = threading.Lock()


class VectorStore:
    """
    Persistent vector store using ChromaDB.

    Safely handles missing ChromaDB installation, provides batch upsert,
    metadata sanitization, and cosine distance queries.
    """

    def __init__(
        self,
        persist_dir: Optional[Union[str, Path]] = None,
        collection_name: Optional[str] = None,
    ):
        """
        Initializes VectorStore with storage directory and collection name.

        Args:
            persist_dir: Filesystem path to persist vector database. Defaults to settings.RAG_INDEX_DIR.
            collection_name: ChromaDB collection name. Defaults to settings.RAG_COLLECTION_NAME.
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
        self._client = None
        self._collection = None
        self._lock = threading.Lock()
        self._init_attempted = False
        self._available = False

    def _ensure_initialized(self) -> None:
        """Lazily connects to ChromaDB and retrieves/creates the collection under thread lock."""
        if self._init_attempted:
            return

        with self._lock:
            if self._init_attempted:
                return

            self._init_attempted = True
            try:
                import chromadb

                self.persist_dir.mkdir(parents=True, exist_ok=True)
                logger.info("Initializing ChromaDB persistent client at: %s", self.persist_dir)

                self._client = chromadb.PersistentClient(path=str(self.persist_dir.resolve()))
                # Use cosine distance space so distance = 1 - cosine_similarity
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                self._available = True
                logger.info("Connected to ChromaDB collection '%s'", self.collection_name)
            except ImportError as exc:
                logger.warning(
                    "chromadb library is not installed (%s). Vector store capabilities will be unavailable.",
                    exc,
                )
                self._client = None
                self._collection = None
                self._available = False
            except Exception as exc:
                logger.error("Failed to initialize ChromaDB at %s: %s", self.persist_dir, exc)
                self._client = None
                self._collection = None
                self._available = False

    def is_available(self) -> bool:
        """
        Checks whether ChromaDB is available and the collection is loaded.

        Returns:
            True if ready, False otherwise.
        """
        self._ensure_initialized()
        return self._available and self._collection is not None

    def add_documents(
        self,
        ids: List[str],
        texts: List[str],
        embeddings: List[List[float]],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        """
        Upserts document chunks, embeddings, and metadata into the collection.

        Sanitizes metadata values to supported primitive types (str, int, float, bool).

        Args:
            ids: List of unique chunk IDs.
            texts: List of chunk text strings.
            embeddings: List of embedding vectors.
            metadatas: List of chunk metadata dictionaries.
        """
        if not ids or not texts:
            logger.debug("add_documents called with empty payload, skipping")
            return

        if not self.is_available():
            logger.warning("VectorStore is unavailable; cannot add documents")
            return

        # Sanitize metadata for ChromaDB (only allows str, int, float, bool)
        clean_metadatas: List[Dict[str, Union[str, int, float, bool]]] = []
        for meta in metadatas:
            clean_m: Dict[str, Union[str, int, float, bool]] = {}
            for k, v in (meta or {}).items():
                if v is None:
                    clean_m[k] = ""
                elif isinstance(v, (str, int, float, bool)):
                    clean_m[k] = v
                else:
                    clean_m[k] = str(v)
            clean_metadatas.append(clean_m)

        try:
            self._collection.upsert(
                ids=ids,
                documents=texts,
                embeddings=embeddings,
                metadatas=clean_metadatas,
            )
            logger.info("Successfully upserted %d documents into '%s'", len(ids), self.collection_name)
        except Exception as exc:
            logger.error("Failed to upsert documents into ChromaDB collection '%s': %s", self.collection_name, exc)

    def query(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        where_filter: Optional[dict] = None,
    ) -> List[dict]:
        """
        Queries the vector store for nearest neighbors to the given query embedding.

        Args:
            query_embedding: Float vector of the search query.
            top_k: Maximum number of chunks to return. Defaults to 5.
            where_filter: Optional metadata filtering dictionary.

        Returns:
            List of dicts: [{'text': str, 'metadata': dict, 'distance': float, 'id': str}]
        """
        if not query_embedding:
            return []

        if not self.is_available():
            logger.warning("VectorStore is unavailable; query returning empty")
            return []

        total_docs = self.count()
        if total_docs == 0:
            logger.debug("Collection '%s' is empty; returning empty query results", self.collection_name)
            return []

        effective_k = max(1, min(top_k, total_docs))

        try:
            query_kwargs: Dict[str, Any] = {
                "query_embeddings": [query_embedding],
                "n_results": effective_k,
            }
            if where_filter:
                query_kwargs["where"] = where_filter

            results = self._collection.query(**query_kwargs)

            docs = results.get("documents", [[]])[0] if results.get("documents") else []
            metas = results.get("metadatas", [[]])[0] if results.get("metadatas") else []
            dists = results.get("distances", [[]])[0] if results.get("distances") else []
            ids = results.get("ids", [[]])[0] if results.get("ids") else []

            output: List[dict] = []
            for i in range(len(docs)):
                output.append({
                    "text": docs[i],
                    "metadata": metas[i] if i < len(metas) and metas[i] is not None else {},
                    "distance": dists[i] if i < len(dists) and dists[i] is not None else 0.0,
                    "id": ids[i] if i < len(ids) else "",
                })

            return output
        except Exception as exc:
            logger.error("Vector store query failed on collection '%s': %s", self.collection_name, exc)
            return []

    def count(self) -> int:
        """
        Returns the total number of documents indexed in the collection.

        Returns:
            Document count, or 0 if unavailable/empty.
        """
        if not self.is_available():
            return 0

        try:
            return self._collection.count()
        except Exception as exc:
            logger.error("Error retrieving count from collection '%s': %s", self.collection_name, exc)
            return 0

    def clear(self) -> None:
        """Deletes all indexed documents from the collection and resets it."""
        if not self.is_available():
            return

        with self._lock:
            try:
                self._client.delete_collection(name=self.collection_name)
                self._collection = self._client.get_or_create_collection(
                    name=self.collection_name,
                    metadata={"hnsw:space": "cosine"},
                )
                logger.info("Successfully cleared collection '%s'", self.collection_name)
            except Exception as exc:
                logger.error("Failed to clear collection '%s': %s", self.collection_name, exc)

    def delete_collection(self) -> None:
        """Removes the collection entirely from ChromaDB."""
        if not self.is_available():
            return

        with self._lock:
            try:
                self._client.delete_collection(name=self.collection_name)
                self._collection = None
                self._available = False
                logger.info("Successfully deleted collection '%s'", self.collection_name)
            except Exception as exc:
                logger.error("Failed to delete collection '%s': %s", self.collection_name, exc)


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
