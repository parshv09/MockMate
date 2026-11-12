"""
Service layer package for MockMate.
Contains business logic extracted from views for clean reuse across Django templates and REST framework APIs.
"""

from .resume_service import (
    ALLOWED_RESUME_EXTENSIONS,
    MAX_RESUME_FILE_SIZE_BYTES,
    cleanup_resume_assets,
    delete_candidate_resume,
    delete_resume_vector_store,
    extract_text_from_resume_file,
    save_and_index_resume,
    validate_resume_file,
)
from .session_service import (
    create_standard_session,
    create_resume_jd_session,
    create_phase_practice_session,
    get_next_unprocessed_answer,
    get_session_summary_data,
    ROLE_MAP,
)
from .answer_service import (
    AnswerAlreadyProcessedError,
    AnswerClaimError,
    AnswerClaimLostError,
    AnswerCurrentlyProcessingError,
    AnswerDatabaseContentionError,
    acquire_answer_claim,
    end_candidate_session,
    release_answer_claim_on_failure,
    renew_answer_claim,
    skip_candidate_question,
    submit_candidate_answer,
)
from .video_service import (
    process_video_frame,
    finalize_session_video_metrics,
    get_session_video_metrics,
    SESSION_VIDEO_STATS,
)
from .report_service import build_session_pdf_report

__all__ = [
    "ALLOWED_RESUME_EXTENSIONS",
    "MAX_RESUME_FILE_SIZE_BYTES",
    "cleanup_resume_assets",
    "delete_candidate_resume",
    "delete_resume_vector_store",
    "extract_text_from_resume_file",
    "save_and_index_resume",
    "validate_resume_file",
    "create_standard_session",
    "create_resume_jd_session",
    "create_phase_practice_session",
    "get_next_unprocessed_answer",
    "get_session_summary_data",
    "ROLE_MAP",
    "submit_candidate_answer",
    "skip_candidate_question",
    "end_candidate_session",
    "process_video_frame",
    "finalize_session_video_metrics",
    "get_session_video_metrics",
    "SESSION_VIDEO_STATS",
    "build_session_pdf_report",
]

