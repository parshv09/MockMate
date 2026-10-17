"""
Text splitter module for the RAG pipeline.

Provides sentence-aware recursive text splitting to chunk documents into optimal
sizes for vector embedding and retrieval, with configurable overlap.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List

from .document_loader import Document

logger = logging.getLogger(__name__)

# Separators ordered from coarse to fine granularity
SEPARATORS = [
    "\n\n",              # Paragraphs
    "\n",                # Lines
    r"(?<=[.!?])\s+",    # Sentence boundaries (preserving punctuation)
    "; ",                # Semicolon clauses
    ", ",                # Comma clauses
    " ",                 # Words
    "",                  # Characters
]


@dataclass
class Chunk:
    """Represents a text chunk produced from splitting a Document."""

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def _recursive_split_text(text: str, separators: List[str], chunk_size: int) -> List[str]:
    """
    Recursively splits text using the first matching separator from the list.

    Args:
        text: Input string to split.
        separators: Priority list of separator patterns.
        chunk_size: Maximum desired character length per chunk.

    Returns:
        List of text pieces, each ideally <= chunk_size.
    """
    if len(text) <= chunk_size:
        stripped = text.strip()
        return [stripped] if stripped else []

    for i, sep in enumerate(separators):
        if sep == "":
            # Character fallback split
            return [
                text[idx : idx + chunk_size].strip()
                for idx in range(0, len(text), chunk_size)
                if text[idx : idx + chunk_size].strip()
            ]

        if sep.startswith("(?<="):
            splits = re.split(sep, text)
        else:
            splits = text.split(sep)

        # Only use this separator if it actually divided the text
        if len(splits) > 1:
            pieces: List[str] = []
            for s in splits:
                s_stripped = s.strip()
                if not s_stripped:
                    continue
                if len(s_stripped) <= chunk_size:
                    pieces.append(s_stripped)
                else:
                    # Recursively split with finer separators
                    pieces.extend(_recursive_split_text(s_stripped, separators[i + 1 :], chunk_size))
            return pieces

    # Fallback if no separator worked
    return [
        text[idx : idx + chunk_size].strip()
        for idx in range(0, len(text), chunk_size)
        if text[idx : idx + chunk_size].strip()
    ]


def _merge_splits(splits: List[str], chunk_size: int, chunk_overlap: int) -> List[str]:
    """
    Merges atomic text segments into chunks <= chunk_size with chunk_overlap.

    Args:
        splits: List of text segments.
        chunk_size: Maximum character length per chunk.
        chunk_overlap: Overlap in characters between adjacent chunks.

    Returns:
        List of merged chunk strings.
    """
    chunks: List[str] = []
    current_chunk: List[str] = []
    current_len = 0

    for split in splits:
        split_len = len(split)
        # Check if adding this segment exceeds chunk_size
        separator_len = 1 if current_chunk else 0
        if current_chunk and (current_len + split_len + separator_len > chunk_size):
            merged = " ".join(current_chunk).strip()
            if merged:
                chunks.append(merged)

            # Keep tail segments to satisfy overlap requirement
            while current_chunk and current_len > chunk_overlap:
                popped = current_chunk.pop(0)
                current_len -= len(popped)
                if current_chunk:
                    current_len -= 1  # Space separator removed

        current_chunk.append(split)
        current_len = sum(len(s) for s in current_chunk) + max(0, len(current_chunk) - 1)

    if current_chunk:
        merged = " ".join(current_chunk).strip()
        if merged and (not chunks or merged != chunks[-1]):
            chunks.append(merged)

    return chunks


def split_text(text: str, chunk_size: int = 800, chunk_overlap: int = 120) -> List[str]:
    """
    Splits raw text into sentence-aware chunks of specified size and overlap.

    Args:
        text: Source text to split.
        chunk_size: Target maximum characters per chunk. Defaults to 800.
        chunk_overlap: Target overlap characters between chunks. Defaults to 120.

    Returns:
        List of non-empty text chunks.
    """
    if not text or not text.strip():
        return []

    if chunk_size <= 0:
        chunk_size = 800

    chunk_overlap = max(0, min(chunk_overlap, chunk_size - 1))

    if len(text) <= chunk_size:
        stripped = text.strip()
        return [stripped] if stripped else []

    atomic_pieces = _recursive_split_text(text, SEPARATORS, chunk_size)
    return _merge_splits(atomic_pieces, chunk_size, chunk_overlap)


def split_documents(
    documents: List[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> List[Chunk]:
    """
    Splits a list of Documents into sentence-aware Chunks with inherited metadata.

    Each chunk receives a unique chunk_id formatted as f"{doc_name}::chunk_{i}"
    and a chunk_index. Empty chunks are skipped.

    Args:
        documents: List of Document objects to split.
        chunk_size: Maximum characters per chunk (default 800).
        chunk_overlap: Characters of overlap between chunks (default 120).

    Returns:
        List of Chunk objects.
    """
    all_chunks: List[Chunk] = []

    for doc in documents:
        doc_name = doc.metadata.get("doc_name", "doc")
        raw_chunks = split_text(doc.text, chunk_size=chunk_size, chunk_overlap=chunk_overlap)

        for i, text_chunk in enumerate(raw_chunks):
            if not text_chunk.strip():
                continue

            chunk_id = f"{doc_name}::chunk_{i}"
            chunk_metadata = {
                **doc.metadata,
                "chunk_id": chunk_id,
                "chunk_index": i,
            }

            all_chunks.append(Chunk(text=text_chunk, metadata=chunk_metadata))

    logger.info("Split %d documents into %d chunks", len(documents), len(all_chunks))
    return all_chunks
