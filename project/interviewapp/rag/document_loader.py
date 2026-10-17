"""
Document loader module for the RAG pipeline.

Loads text and markdown files recursively from a base directory, extracts
metadata, normalizes content, and returns structured Document objects.
"""

import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Union

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".txt", ".md"}


@dataclass
class Document:
    """Represents a loaded source document with content and metadata."""

    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)


def _normalize_text(content: str) -> str:
    """
    Normalizes whitespace and newline characters in document content.

    Args:
        content: Raw text content from file.

    Returns:
        Cleaned text content with normalized newlines and trimmed whitespace.
    """
    # Normalize Windows and legacy Mac newlines to Unix newlines
    normalized = re.sub(r"\r\n?", "\n", content)
    # Collapse 3 or more consecutive blank lines into 2
    normalized = re.sub(r"\n{3,}", "\n\n", normalized)
    return normalized.strip()


def load_documents(base_dir: Union[Path, str]) -> List[Document]:
    """
    Recursively loads all .txt and .md files from base_dir into Document objects.

    Infers 'topic' from the parent directory name (e.g. knowledge_base/python/basics.md -> topic='python').
    Normalizes whitespace, strips empty content, logs warnings for unreadable files,
    and returns an empty list if the directory does not exist.

    Args:
        base_dir: Root directory path containing knowledge documents.

    Returns:
        List of Document instances containing loaded text and metadata.
    """
    base_path = Path(base_dir)

    if not base_path.exists():
        logger.warning("Knowledge base directory does not exist: %s", base_path)
        return []

    if not base_path.is_dir():
        logger.warning("Knowledge base path is not a directory: %s", base_path)
        return []

    documents: List[Document] = []
    base_path_resolved = base_path.resolve()

    logger.info("Scanning for documents in: %s", base_path_resolved)

    for root, _, files in os.walk(base_path_resolved):
        root_path = Path(root)
        for filename in sorted(files):
            file_path = root_path / filename
            suffix = file_path.suffix.lower()

            if suffix not in SUPPORTED_EXTENSIONS:
                continue

            try:
                # Attempt reading with utf-8, fallback to latin-1 if needed
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        raw_text = f.read()
                except UnicodeDecodeError:
                    logger.warning("UTF-8 decoding failed for %s, falling back to latin-1", file_path)
                    with open(file_path, "r", encoding="latin-1") as f:
                        raw_text = f.read()

                normalized_text = _normalize_text(raw_text)
                if not normalized_text:
                    logger.debug("Skipping empty document: %s", file_path)
                    continue

                # Infer topic from parent directory
                if root_path == base_path_resolved:
                    topic = "general"
                else:
                    topic = root_path.name.lower()

                metadata = {
                    "doc_name": file_path.name,
                    "topic": topic,
                    "source_path": str(file_path),
                    "file_type": suffix.lstrip("."),
                }

                documents.append(Document(text=normalized_text, metadata=metadata))
                logger.debug("Loaded document '%s' with topic '%s' (%d chars)", file_path.name, topic, len(normalized_text))

            except (OSError, PermissionError) as exc:
                logger.warning("Failed to read file %s: %s", file_path, exc)
                continue
            except Exception as exc:
                logger.warning("Unexpected error loading file %s: %s", file_path, exc)
                continue

    logger.info("Successfully loaded %d documents from %s", len(documents), base_path_resolved)
    return documents
