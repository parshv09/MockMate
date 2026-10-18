"""
Resume RAG (Retrieval-Augmented Generation) module.

Chunks, embeds, and indexes candidate resumes into dedicated persistent vector stores.
Retrieves relevant candidate experience, projects, and skills matching a target Job
Description, and formulates deeply grounded, personalized mock interview questions.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional

from django.conf import settings

from ..qgen_groq import (
    _call_groq_chat,
    _extract_json_array_from_text,
    _validate_question_obj,
    generate_resume_jd_questions_groq,
)
from .embeddings import get_embedding_model
from .text_splitter import split_text
from .validators import validate_and_deduplicate
from .vector_store import VectorStore

logger = logging.getLogger(__name__)


def get_resume_vector_store(resume_id: int) -> VectorStore:
    """
    Returns a dedicated VectorStore instance for a specific Resume ID.
    Stored under rag_index/resumes/resume_{id}/.
    """
    base_dir = getattr(settings, "RAG_INDEX_DIR", settings.BASE_DIR / "rag_index")
    resume_index_dir = Path(base_dir) / "resumes" / f"resume_{resume_id}"
    return VectorStore(persist_dir=resume_index_dir, collection_name=f"resume_{resume_id}")


def index_resume(resume_obj) -> int:
    """
    Chunks and embeds a candidate's resume text, storing it in a persistent vector index.

    Args:
        resume_obj: Resume model instance containing id and extracted_text.

    Returns:
        Number of indexed chunks.
    """
    text = (resume_obj.extracted_text or "").strip()
    if not text:
        logger.warning("Resume #%s has empty extracted text; skipping indexing", resume_obj.id)
        return 0

    chunks = split_text(text, chunk_size=500, chunk_overlap=80)
    if not chunks:
        logger.warning("No chunks produced for resume #%s", resume_obj.id)
        return 0

    embed_model = get_embedding_model()
    if not embed_model.is_available():
        logger.warning("Embedding model unavailable; cannot index resume #%s", resume_obj.id)
        return 0

    embeddings = embed_model.embed_texts(chunks)
    if not embeddings:
        logger.warning("Failed to generate embeddings for resume #%s", resume_obj.id)
        return 0

    store = get_resume_vector_store(resume_obj.id)
    store.clear()

    chunk_ids = [f"resume_{resume_obj.id}::chunk_{i}" for i in range(len(chunks))]
    metadatas = [
        {
            "resume_id": resume_obj.id,
            "title": resume_obj.title,
            "chunk_index": i,
        }
        for i in range(len(chunks))
    ]

    store.add_documents(
        ids=chunk_ids,
        texts=chunks,
        embeddings=embeddings,
        metadatas=metadatas,
    )

    logger.info("Successfully indexed %d chunks for Resume #%s ('%s')", len(chunks), resume_obj.id, resume_obj.title)
    return len(chunks)


def retrieve_resume_context_for_jd(
    resume_obj,
    job_description: str,
    top_k: int = 5,
) -> List[Dict]:
    """
    Retrieves the most relevant passages from the candidate's resume that match
    or contrast with the requirements and tech stack in the Job Description.

    Args:
        resume_obj: Resume model instance.
        job_description: Plain text job description.
        top_k: Number of relevant chunks to retrieve.

    Returns:
        List of candidate resume chunk dictionaries with text and metadata.
    """
    store = get_resume_vector_store(resume_obj.id)
    if store.count() == 0:
        logger.info("Resume #%s index is empty; triggering automatic indexing", resume_obj.id)
        count = index_resume(resume_obj)
        if count == 0:
            return []

    embed_model = get_embedding_model()
    if not embed_model.is_available():
        return []

    # Construct search query focusing on technical competencies from JD
    jd_clean = " ".join((job_description or "").split())
    if not jd_clean:
        jd_clean = "core technical projects, software development experience, frameworks, and architecture"

    # Take first ~1000 characters of JD for semantic embedding
    query_text = jd_clean[:1000]
    query_vec = embed_model.embed_query(query_text)
    if not query_vec:
        return []

    results = store.query(query_embedding=query_vec, top_k=top_k)
    logger.info("Retrieved %d matching resume chunks for Resume #%s against JD", len(results), resume_obj.id)
    return results


def build_resume_jd_rag_prompt(
    resume_chunks: List[Dict],
    job_description: str,
    n: int = 5,
    difficulty: int = 3,
    previous_questions: Optional[List[str]] = None,
) -> str:
    """
    Constructs a grounded Groq prompt cross-examining candidate's resume against the target JD.
    """
    diff_val = max(1, min(5, int(difficulty or 3)))

    if diff_val <= 2:
        diff_instruction = (
            "Questions should be introductory to intermediate. Focus on foundational concepts behind "
            "the technologies the candidate used in their projects, their specific contribution, and basic problem solving."
        )
    elif diff_val <= 4:
        diff_instruction = (
            "Questions should test practical engineering depth, design trade-offs, architecture choices, "
            "debugging tough issues, and how their resume projects fulfill key requirements in the Job Description."
        )
    else:
        diff_instruction = (
            "Questions should be deeply technical and rigorous. Challenge the candidate on scalability, concurrency, "
            "system bottlenecks, failure modes, security, and edge cases in the projects they claimed on their resume."
        )

    # Format retrieved resume passages
    formatted_resume_blocks = []
    for idx, c in enumerate(resume_chunks, 1):
        c_text = c.get("text", "").strip()
        if c_text:
            formatted_resume_blocks.append(f"[Resume Excerpt {idx}]:\n{c_text}")

    resume_text = "\n\n".join(formatted_resume_blocks) if formatted_resume_blocks else "Candidate resume summary not available."

    avoid_clause = ""
    if previous_questions:
        clean_pqs = [str(q).strip() for q in previous_questions if str(q).strip()]
        if clean_pqs:
            avoid_clause = "\n- Do NOT generate questions similar to previously asked questions:\n"
            for pq in clean_pqs:
                avoid_clause += f"  * {pq}\n"

    prompt = f"""
You are an expert technical interviewer conducting a high-stakes job interview.
You have the candidate's verified RESUME EXCERPTS and the hiring company's TARGET JOB DESCRIPTION.

=== TARGET JOB DESCRIPTION (WHAT THE ROLE REQUIRES) ===
{job_description[:3000]}
=== END JOB DESCRIPTION ===

=== CANDIDATE RESUME EVIDENCE (RETRIEVED CONTEXT) ===
{resume_text}
=== END RESUME EVIDENCE ===

Difficulty Level:
{diff_instruction}

Interviewer Guidelines:
- Generate EXACTLY {n} rigorous, realistic interview questions.
- Every question MUST directly probe the candidate's real projects, tools, frameworks, and roles listed in the RESUME EVIDENCE as they relate to the JOB DESCRIPTION.
- Do NOT ask generic textbook trivia (e.g. avoid 'What is a REST API?'). Instead, ask grounded experiential questions (e.g. 'In your E-Commerce project, you built a microservice with FastAPI and Redis; how did you handle cache invalidation during high traffic?').
- Probe any technical gaps between what the candidate did on their resume and what the Job Description demands.
- Keep questions clear, conversational, and answerable within 3-5 minutes.
{avoid_clause}
- Each question must include target keywords the candidate should mention in their answer.
- Type must be "reasoning".

Return ONLY a valid JSON array of objects in this exact format:
[
  {{
    "text": "The detailed interview question",
    "keywords": "keyword1,keyword2,keyword3",
    "difficulty": {diff_val},
    "type": "reasoning"
  }}
]
""".strip()

    return prompt


def generate_resume_jd_rag_questions(
    resume_obj,
    job_description: str,
    n: int = 5,
    difficulty: int = 3,
    previous_questions: Optional[List[str]] = None,
    model: Optional[str] = None,
) -> List[Dict]:
    """
    Main entrypoint for generating Resume + JD grounded interview questions.
    Retrieves candidate resume chunks matching the JD, queries Groq, and validates results.
    Falls back gracefully to standard Groq generation if retrieval yields insufficient context.
    """
    try:
        # Step 1: Retrieve matching resume context chunks
        chunks = retrieve_resume_context_for_jd(
            resume_obj=resume_obj,
            job_description=job_description,
            top_k=max(n, 5),
        )

        if not chunks:
            logger.warning("No matching resume chunks retrieved for Resume #%s; falling back to non-RAG", resume_obj.id)
            return generate_resume_jd_questions_groq(
                resume_text=resume_obj.extracted_text,
                job_description=job_description,
                n=n,
                difficulty=difficulty,
            )

        # Step 2: Build grounded RAG prompt
        prompt = build_resume_jd_rag_prompt(
            resume_chunks=chunks,
            job_description=job_description,
            n=n,
            difficulty=difficulty,
            previous_questions=previous_questions,
        )

        logger.info(
            "Invoking Groq chat for Resume RAG (Resume #%s, n=%d, difficulty=%d, chunks=%d)",
            resume_obj.id,
            n,
            difficulty,
            len(chunks),
        )

        raw_response = _call_groq_chat(prompt=prompt, model=model, temperature=0.7)
        if not raw_response or not raw_response.strip():
            logger.error("Groq chat returned empty response for Resume RAG")
            raise ValueError("Empty Groq response")

        parsed_items = _extract_json_array_from_text(raw_response)
        validated_raw: List[Dict] = []
        for item in parsed_items:
            valid_q = _validate_question_obj(item)
            if valid_q:
                validated_raw.append(valid_q)

        validated_questions = validate_and_deduplicate(
            questions=validated_raw,
            n=n,
            previous_questions=previous_questions,
        )

        if len(validated_questions) >= n:
            logger.info("Resume RAG successfully generated %d questions", len(validated_questions[:n]))
            return validated_questions[:n]

        logger.warning("Resume RAG produced %d/%d questions; augmenting with fallback", len(validated_questions), n)

    except Exception as exc:
        logger.exception("Error in generate_resume_jd_rag_questions: %s", exc)

    # Fallback to direct prompt if RAG failed or was incomplete
    return generate_resume_jd_questions_groq(
        resume_text=resume_obj.extracted_text,
        job_description=job_description,
        n=n,
        difficulty=difficulty,
    )
