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
        level_title = "ENTRY-LEVEL / INTERN / FRESH GRADUATE (0-1 Years Experience)"
        diff_instruction = f"""
TARGET CANDIDATE LEVEL: {level_title}
DIFFICULTY SCORE: {diff_val}/5 (BEGINNER / FUNDAMENTAL)

CRITICAL DIFFICULTY CONSTRAINTS:
- Questions MUST be basic, welcoming, and appropriate for an entry-level candidate or intern.
- Focus on fundamental concepts, basic definitions, what tools they used, what their personal contribution was in their project, and how they learned the technologies.
- Ask them to explain how their project works at a high level, how they wrote simple functions or queries, or how they fixed a simple bug.
- STRICT PROHIBITIONS FOR ENTRY-LEVEL:
  * ABSOLUTELY DO NOT ask about distributed systems, microservices, high-traffic scaling, cache invalidation, load balancing, multi-threaded concurrency, or system architecture trade-offs.
  * DO NOT ask aggressive, senior-level grilling questions.
- Good Entry-Level Question Example: "On your resume you listed Python and MySQL for your web project. Can you explain how your application connects to the database, and what a foreign key was used for?"
- Good Entry-Level Question Example: "In your frontend project, how did you handle user input and what is the difference between props and state?"
"""
    elif diff_val <= 4:
        level_title = "MID-LEVEL DEVELOPER (2-4 Years Experience)"
        diff_instruction = f"""
TARGET CANDIDATE LEVEL: {level_title}
DIFFICULTY SCORE: {diff_val}/5 (INTERMEDIATE PRACTICAL)

CRITICAL DIFFICULTY CONSTRAINTS:
- Questions should test practical development knowledge, real-world implementation, and best practices.
- Ask about REST API structure, error handling, database indexing, testing strategies, state management, and edge-case handling in their resume projects.
- Probe how their experience aligns with the core requirements in the Job Description.
"""
    else:
        level_title = "SENIOR / LEAD ENGINEER (5+ Years Experience)"
        diff_instruction = f"""
TARGET CANDIDATE LEVEL: {level_title}
DIFFICULTY SCORE: {diff_val}/5 (ADVANCED / SENIOR EXPERT)

CRITICAL DIFFICULTY CONSTRAINTS:
- Questions must be deeply technical, challenging, and architecture-focused.
- Challenge the candidate on concurrency, high-throughput scaling, database bottlenecks, distributed caching, fault tolerance, security, and architectural trade-offs.
"""

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
You are an expert technical interviewer conducting an interview calibrated specifically for a {level_title}.
You have the candidate's verified RESUME EVIDENCE and the hiring company's TARGET JOB DESCRIPTION.

=== TARGET JOB DESCRIPTION ===
{job_description[:3000]}
=== END JOB DESCRIPTION ===

=== CANDIDATE RESUME EVIDENCE (RETRIEVED CONTEXT) ===
{resume_text}
=== END RESUME EVIDENCE ===

=== DIFFICULTY & LEVEL SPECIFICATION ===
{diff_instruction}
=== END DIFFICULTY SPECIFICATION ===

Interviewer Guidelines:
- Generate EXACTLY {n} questions tailored to the candidate's resume and job description.
- Every question must be strictly calibrated to the {level_title} difficulty criteria defined above.
- Relate questions to the tools, languages, and projects listed on the candidate's resume.
- Keep questions clear, focused, and answerable within 2-4 minutes.
{avoid_clause}
- Each question must include target keywords the candidate should mention in their answer.
- Type must be "reasoning".

Return ONLY a valid JSON array of objects in this exact format:
[
  {{
    "text": "The interview question text",
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
