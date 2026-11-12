import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
from django.conf import settings
from django.db import transaction
from ..models import Resume

logger = logging.getLogger(__name__)

ALLOWED_RESUME_EXTENSIONS = {".pdf", ".txt", ".md"}
MAX_RESUME_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB

try:
    from ..rag import delete_resume_vector_store, index_resume
    _rag_available = True
except ImportError:
    _rag_available = False
    def delete_resume_vector_store(resume_id: int) -> bool:
        return False


def validate_resume_file(file_obj) -> None:
    """
    Centralized validation for resume file uploads.
    Used consistently by DRF API serializers and Django template views.

    Enforces:
    1. Extension constraint: must be .pdf, .txt, or .md.
    2. Size constraint: <= 10 MB.
    3. PDF magic-byte header: .pdf files must start with %PDF.
    4. File pointer reset: file_obj.seek(0) is guaranteed via try...finally.

    Raises:
        ValueError: with a clear message if validation fails.
    """
    if not file_obj:
        return

    name = getattr(file_obj, "name", "")
    ext = os.path.splitext(name)[1].lower() if name else ""

    # 1. Extension check
    if not ext or ext not in ALLOWED_RESUME_EXTENSIONS:
        allowed_str = ", ".join(sorted(ALLOWED_RESUME_EXTENSIONS))
        raise ValueError(f"Unsupported file format '{ext}'. Allowed extensions are: {allowed_str}.")

    # 2. Size check
    size = getattr(file_obj, "size", None)
    if size is None and hasattr(file_obj, "seek") and hasattr(file_obj, "tell"):
        pos = file_obj.tell()
        file_obj.seek(0, os.SEEK_END)
        size = file_obj.tell()
        file_obj.seek(pos)

    if size is not None and size > MAX_RESUME_FILE_SIZE_BYTES:
        raise ValueError("File size exceeds maximum allowed limit of 10 MB.")

    # 3. PDF Header Magic-Byte validation (%PDF)
    if ext == ".pdf":
        header = b""
        try:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)
            header = file_obj.read(5)
        except Exception as exc:
            raise ValueError(f"Could not read PDF header: {exc}")
        finally:
            if hasattr(file_obj, "seek"):
                file_obj.seek(0)

        if not header.startswith(b"%PDF"):
            raise ValueError("Invalid PDF file content. The file does not have a valid %PDF header.")


def extract_text_from_resume_file(file_obj) -> str:
    """
    Extract raw text from uploaded PDF, TXT, or MD resume file.
    Validates PDF magic bytes before attempting PDF parsing.
    Ensures file pointer is always reset to position 0.
    """
    if not file_obj:
        return ""

    filename = getattr(file_obj, "name", "").lower()
    text = ""

    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass

    if filename.endswith(".pdf"):
        # 1. Verify PDF magic bytes header (%PDF)
        header = b""
        try:
            header = file_obj.read(5)
        except Exception as e:
            logger.warning("Failed to read header from '%s': %s", filename, e)
        finally:
            if hasattr(file_obj, "seek"):
                try:
                    file_obj.seek(0)
                except Exception:
                    pass

        if not header.startswith(b"%PDF"):
            logger.warning("File '%s' has .pdf extension but lacks %%PDF header. Rejecting as malformed.", filename)
            return ""

        # 2. Extract text using pypdf or PyPDF2 (do not fall back to raw binary decoding)
        try:
            import pypdf
            reader = pypdf.PdfReader(file_obj)
            pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
            text = "\n".join(pages_text)
        except ImportError:
            # Fallback to PyPDF2
            try:
                import PyPDF2
                reader = PyPDF2.PdfReader(file_obj)
                pages_text = [page.extract_text() for page in reader.pages if page.extract_text()]
                text = "\n".join(pages_text)
            except ImportError:
                logger.warning("Neither pypdf nor PyPDF2 is installed; cannot extract text from PDF.")
                text = ""
            except Exception as e:
                logger.warning("PyPDF2 extraction error for '%s': %s", filename, e)
                text = ""
        except Exception as e:
            logger.warning("pypdf extraction error for '%s': %s", filename, e)
            text = ""
    else:
        try:
            text = file_obj.read().decode("utf-8", errors="ignore")
        except Exception:
            text = ""

    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:
            pass

    return text.strip()


def save_and_index_resume(
    user,
    title: str = "",
    file_obj=None,
    raw_text: str = "",
    resume_file=None,
    pasted_text: str = "",
) -> Optional[Resume]:
    """
    Extracts text from file (if provided), combines with raw text,
    persists a Resume instance for the user, and triggers ChromaDB vector indexing.
    Supports both file_obj/resume_file and raw_text/pasted_text argument aliases.
    Validates uploaded file before persistence.
    """
    actual_file = file_obj if file_obj is not None else resume_file
    actual_text = raw_text or pasted_text

    if actual_file:
        validate_resume_file(actual_file)

    extracted = extract_text_from_resume_file(actual_file) if actual_file else ""
    full_text = f"{extracted}\n{actual_text}".strip()

    if not full_text:
        return None

    resolved_title = (title or (getattr(actual_file, "name", "") if actual_file else "") or "Uploaded Resume").strip()
    resume_obj = Resume.objects.create(
        user=user,
        title=resolved_title[:150],
        original_file=actual_file if actual_file else None,
        extracted_text=full_text,
    )

    if _rag_available:
        try:
            index_resume(resume_obj)
        except Exception as e:
            logger.exception("Failed to index resume #%s into ChromaDB: %s", resume_obj.id, e)

    return resume_obj


def cleanup_resume_assets(
    resume_id: int,
    file_field=None,
    file_path: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Idempotent asset cleanup helper for a deleted resume.
    Can be run via transaction.on_commit() or invoked directly for cleanup retries.

    Cleans:
    1. Dedicated ChromaDB vector store directory (rag_index/resumes/resume_{resume_id})
    2. Physical uploaded resume file from media storage

    Returns a dict detailing cleanup status:
    {
        "resume_id": int,
        "vector_cleaned": bool,
        "file_cleaned": bool,
        "all_cleaned": bool,
        "errors": List[str],
    }
    """
    errors: List[str] = []
    vector_cleaned = False
    file_cleaned = False

    # 1. Clean vector store
    base_dir = getattr(settings, "RAG_INDEX_DIR", settings.BASE_DIR / "rag_index")
    target_vec_dir = Path(base_dir) / "resumes" / f"resume_{resume_id}"

    if _rag_available:
        try:
            res = delete_resume_vector_store(resume_id)
            if res:
                vector_cleaned = True
            else:
                errors.append(f"Vector store cleanup returned False for Resume #{resume_id}")
        except Exception as exc:
            logger.exception("Exception during vector cleanup for Resume #%s: %s", resume_id, exc)
            errors.append(f"Vector cleanup exception: {exc}")
    else:
        # Check if index directory actually exists on disk
        if target_vec_dir.exists():
            errors.append(f"RAG unavailable; vector store directory {target_vec_dir} could not be cleaned.")
            vector_cleaned = False
        else:
            vector_cleaned = True

    # 2. Clean physical file
    if file_field and getattr(file_field, "name", ""):
        try:
            file_field.delete(save=False)
            file_cleaned = True
        except Exception as exc:
            logger.exception("Failed to delete physical media file for Resume #%s: %s", resume_id, exc)
            errors.append(f"Media file deletion error: {exc}")
    else:
        file_cleaned = True

    all_cleaned = vector_cleaned and file_cleaned
    if not all_cleaned:
        logger.error(
            "Asset cleanup incomplete for Resume #%s. Vector cleaned: %s, File cleaned: %s. Errors: %s",
            resume_id,
            vector_cleaned,
            file_cleaned,
            errors,
        )
    else:
        logger.info("Successfully cleaned all assets for Resume #%s.", resume_id)

    return {
        "resume_id": resume_id,
        "vector_cleaned": vector_cleaned,
        "file_cleaned": file_cleaned,
        "all_cleaned": all_cleaned,
        "errors": errors,
    }


def delete_candidate_resume(resume_obj) -> bool:
    """
    Database-first atomic deletion of a candidate resume:
    1. Captures resume ID and original file reference before deletion.
    2. Deletes the Resume database record within transaction.atomic().
    3. Schedules cleanup_resume_assets() via transaction.on_commit().
    4. If database deletion fails, filesystem assets are never touched.
    """
    resume_id = resume_obj.id
    file_field = resume_obj.original_file

    with transaction.atomic():
        resume_obj.delete()
        transaction.on_commit(lambda: cleanup_resume_assets(resume_id, file_field=file_field))

    logger.info("Successfully deleted Resume #%s from database; asset cleanup scheduled on commit.", resume_id)
    return True


