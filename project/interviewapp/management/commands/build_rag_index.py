"""
Django management command to build or update the RAG knowledge base vector index.

Usage:
    python manage.py build_rag_index [--clear] [--kb-dir PATH]
"""

import time
import logging
from pathlib import Path
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Build or rebuild the RAG knowledge base vector index using ChromaDB and SentenceTransformers"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear the existing vector collection before indexing",
        )
        parser.add_argument(
            "--kb-dir",
            type=str,
            default=None,
            help="Custom path to the knowledge base directory (defaults to settings.KNOWLEDGE_BASE_DIR)",
        )
        parser.add_argument(
            "--chunk-size",
            type=int,
            default=None,
            help="Chunk size in characters (defaults to settings.RAG_CHUNK_SIZE)",
        )
        parser.add_argument(
            "--chunk-overlap",
            type=int,
            default=None,
            help="Chunk overlap in characters (defaults to settings.RAG_CHUNK_OVERLAP)",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== MockMate RAG Knowledge Base Indexer ==="))
        start_time = time.time()

        # 1. Determine directories and options
        kb_dir_opt = options.get("kb_dir")
        if kb_dir_opt:
            kb_dir = Path(kb_dir_opt)
        else:
            kb_dir = getattr(settings, "KNOWLEDGE_BASE_DIR", settings.BASE_DIR / "knowledge_base")

        chunk_size = options.get("chunk_size") or getattr(settings, "RAG_CHUNK_SIZE", 800)
        chunk_overlap = options.get("chunk_overlap") or getattr(settings, "RAG_CHUNK_OVERLAP", 120)

        if not kb_dir.exists():
            raise CommandError(f"Knowledge base directory does not exist: {kb_dir}")

        self.stdout.write(f"Knowledge Base Directory: {kb_dir}")
        self.stdout.write(f"Chunk Size: {chunk_size} | Chunk Overlap: {chunk_overlap}")

        # 2. Check dependencies
        try:
            from interviewapp.rag.document_loader import load_documents
            from interviewapp.rag.text_splitter import split_documents
            from interviewapp.rag.embeddings import get_embedding_model
            from interviewapp.rag.vector_store import get_vector_store
        except ImportError as e:
            raise CommandError(
                f"Failed to import RAG components: {e}. Please ensure sentence-transformers and chromadb are installed."
            )

        # 3. Load documents
        self.stdout.write("Loading documents...")
        docs = load_documents(kb_dir)
        if not docs:
            self.stdout.write(self.style.WARNING(f"No valid markdown/text documents found in {kb_dir}."))
            return

        self.stdout.write(self.style.SUCCESS(f"Loaded {len(docs)} document(s)."))

        # 4. Split documents into chunks
        self.stdout.write("Splitting documents into chunks...")
        chunks = split_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        if not chunks:
            self.stdout.write(self.style.WARNING("No chunks produced from loaded documents."))
            return

        self.stdout.write(self.style.SUCCESS(f"Generated {len(chunks)} chunk(s)."))

        # 5. Access embedding model
        self.stdout.write("Initializing embedding model...")
        embedding_model = get_embedding_model()
        if not embedding_model.is_available():
            raise CommandError(
                "Embedding model is unavailable. Ensure 'sentence-transformers' and PyTorch are installed."
            )

        # 6. Access vector store
        self.stdout.write("Initializing vector store...")
        store = get_vector_store()

        if options.get("clear"):
            self.stdout.write("Clearing existing vector collection...")
            store.clear()
            self.stdout.write(self.style.SUCCESS("Cleared existing collection."))

        # 7. Generate embeddings
        self.stdout.write(f"Embedding {len(chunks)} chunks in batches...")
        chunk_texts = [c.text for c in chunks]
        embeddings = embedding_model.embed_texts(chunk_texts)

        # 8. Upsert chunks into vector store
        self.stdout.write("Upserting chunks into ChromaDB...")
        chunk_ids = [c.metadata.get("chunk_id", f"chunk_{i}") for i, c in enumerate(chunks)]
        metadatas = [c.metadata for c in chunks]

        store.add_documents(
            ids=chunk_ids,
            texts=chunk_texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

        total_stored = store.count()
        elapsed = time.time() - start_time

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully indexed {len(chunks)} chunk(s) across {len(docs)} document(s) in {elapsed:.2f}s."
            )
        )
        self.stdout.write(self.style.SUCCESS(f"Total documents in collection: {total_stored}"))
