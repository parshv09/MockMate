# interviewapp/nlp_utils.py
import spacy
nlp = spacy.load("en_core_web_sm")
FILLERS = {"um","uh","like","you know","hmm"}


from interviewapp.qgen_groq import _call_groq_chat
import json

def generate_ai_improvement_tips(answer_text, question_text, score):
    """
    Generate dynamic improvement tips using LLM.
    Returns a list of short actionable tips.
    """
    prompt = f"""
You are an expert interview coach.

Question:
{question_text}

Candidate Answer:
{answer_text}

Score: {score}/100

TASK:
Generate 3–5 concise, actionable improvement tips to help the candidate improve.
Tips should be:
- Specific to the answer
- Practical and short
- Focused on clarity, structure, depth, and correctness

Return ONLY a JSON array of strings.
Example:
[
  "Explain the concept step by step",
  "Add a real-world example",
  "Mention trade-offs clearly"
]
"""

    try:
        response = _call_groq_chat(prompt)
        start = response.find("[")
        end = response.rfind("]")
        if start != -1 and end > start:
            tips = json.loads(response[start:end+1])
            if isinstance(tips, list):
                return tips[:5]
    except Exception:
        pass

    return []

def evaluate_semantic_correctness(question_text, answer_text, keywords_list):
    """
    Evaluate the correctness and completeness of the candidate's answer using Groq LLM.
    Returns a score out of 65.
    """
    if not question_text or not answer_text:
        return 0

    keywords_str = ", ".join(keywords_list) if keywords_list else "None"
    prompt = f"""
You are an expert interview coach.

Evaluate the correctness, accuracy, and completeness of the candidate's answer for the given question.
Consider if the answer addresses the question correctly and fits the context of expected keywords/themes.

Question:
{question_text}

Expected Keywords/Themes:
{keywords_str}

Candidate Answer:
{answer_text}

TASK:
Rate the answer on a scale of 0 to 65 points based on its factual correctness and relevance:
- 55–65: Excellent, highly accurate, complete, and covers key concepts.
- 40–54: Good, mostly correct, covers the main points but lacks minor detail.
- 25–39: Average/Partial, has correct ideas but is shallow, incomplete, or slightly off-topic.
- 1–24: Poor, highly inaccurate, or barely relevant.
- 0: Completely incorrect, irrelevant, or empty.

Return ONLY valid JSON in this format:
{{
  "correctness_score": <integer score between 0 and 65>
}}
"""
    try:
        response = _call_groq_chat(prompt)
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end > start:
            data = json.loads(response[start:end+1])
            score = int(data.get("correctness_score", 0))
            return max(0, min(65, score))
    except Exception:
        # Fallback code will handle if -1 is returned
        return -1


def evaluate_resume_grounded_answer(
    question_text: str,
    answer_text: str,
    keywords_list: list,
    resume_chunks: list,
    job_description: str = "",
) -> dict:
    """
    Cross-evaluates the candidate's answer against the actual evidence from their resume.
    Returns structured verification results:
      - correctness_score: 0–45
      - consistency_score: 0–20
      - alignment_level: "high" | "partial" | "low"
      - supported_claims: list of confirmed claims
      - contradictions: list of discrepancies
      - missed_resume_points: list of resume accomplishments omitted from answer
      - analyzed_chunk: concatenated excerpt text used for evaluation
    """
    if not question_text or not answer_text or not resume_chunks:
        return None

    # Format resume excerpts for prompt
    resume_excerpts = []
    for idx, c in enumerate(resume_chunks, 1):
        c_text = (c.get("text") or "").strip()
        if c_text:
            resume_excerpts.append(f"[Resume Excerpt {idx}]:\n{c_text}")
    resume_context_str = "\n\n".join(resume_excerpts) if resume_excerpts else "No resume excerpt available."

    keywords_str = ", ".join(keywords_list) if keywords_list else "None"
    jd_snippet = job_description[:800] if job_description else "Target Job Profile"

    prompt = f"""
You are an expert technical interviewer cross-evaluating a candidate's verbal answer against their verified RESUME CLAIMS.

=== TARGET JOB CONTEXT ===
{jd_snippet}
=== END JOB CONTEXT ===

=== CANDIDATE RESUME EVIDENCE ===
{resume_context_str}
=== END RESUME EVIDENCE ===

Question:
{question_text}

Expected Key Concepts:
{keywords_str}

Candidate Spoken Answer:
{answer_text}

TASK:
1. Correctness Score (0 to 45 points):
   - Evaluate technical accuracy, depth, and relevance to the question.
2. Resume Consistency Score (0 to 20 points):
   - 16–20: Substantively consistent with resume claims; clearly explains technologies, architecture, and projects listed on resume.
   - 10–15: Partial consistency; aligns generally, but omits key accomplishments or metrics stated on the resume.
   - 1–9: Significant discrepancy; contradicts resume claims or fails to explain tools they claimed to have used.
   - 0: Completely fabricated or contradicts resume experience.
3. Identify:
   - supported_claims: 1-3 short bullet strings of resume skills/projects the candidate successfully substantiated.
   - contradictions: short strings of direct discrepancies or exaggerations (empty if none).
   - missed_resume_points: 1-3 short strings of key tools/metrics from their resume relevant to this question that they forgot to mention.

Return ONLY valid JSON in this exact structure:
{{
  "correctness_score": <integer 0-45>,
  "consistency_score": <integer 0-20>,
  "alignment_level": "<high|partial|low>",
  "supported_claims": ["claim 1", "claim 2"],
  "contradictions": [],
  "missed_resume_points": ["point 1"]
}}
"""
    try:
        response = _call_groq_chat(prompt, temperature=0.2)
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end > start:
            data = json.loads(response[start:end+1])
            correctness = max(0, min(45, int(data.get("correctness_score", 0))))
            consistency = max(0, min(20, int(data.get("consistency_score", 0))))
            
            level = str(data.get("alignment_level", "")).lower()
            if level not in ("high", "partial", "low"):
                level = "high" if consistency >= 16 else ("partial" if consistency >= 10 else "low")

            analyzed_snippet = resume_chunks[0].get("text", "")[:350] if resume_chunks else ""

            return {
                "correctness_score": correctness,
                "consistency_score": consistency,
                "alignment_level": level,
                "supported_claims": [str(c) for c in data.get("supported_claims", []) if str(c).strip()][:3],
                "contradictions": [str(c) for c in data.get("contradictions", []) if str(c).strip()][:3],
                "missed_resume_points": [str(p) for p in data.get("missed_resume_points", []) if str(p).strip()][:3],
                "analyzed_chunk": analyzed_snippet
            }
    except Exception as exc:
        import logging
        logging.getLogger(__name__).warning("Grounded resume evaluation failed: %s", exc)

    return None


def generate_expected_answer(question_text: str, role: str = "", keywords_list: list = None) -> str:
    """
    Generate an ideal / expected model answer for an interview question.
    """
    if not question_text:
        return "No specific model answer available."

    keywords_str = ", ".join(keywords_list) if keywords_list else ""
    prompt = f"""
You are an expert interview coach and senior technical interviewer.

Question:
{question_text}

Target Role: {role or 'General'}
Key Concepts/Themes: {keywords_str or 'N/A'}

TASK:
Write an ideal, high-scoring sample model answer (2–3 clear paragraphs or bullet points) that a strong candidate should provide for this question.
Be structured, clear, practical, and direct.

Return ONLY the plain text of the model answer (no JSON, no intro text).
"""
    try:
        response = _call_groq_chat(prompt, temperature=0.3)
        if response and response.strip():
            return response.strip()
    except Exception:
        pass

    # Fallback response if LLM call is unavailable
    if keywords_list:
        return f"A complete answer should address key concepts such as: {', '.join(keywords_list)}. Structure your response using the STAR method (Situation, Task, Action, Result) or state the core definition, key benefits, and practical use cases."
    return "A top-scoring answer should clearly define the core concept, discuss key principles or trade-offs, and provide a concrete example from real-world practice."


def analyze_transcript(text, question, resume=None, job_description=""):
    # ---------- CASE: NO ANSWER ----------
    if not text or text.strip() in ["[Skipped]", "[Voice answer could not be transcribed]", "No answer provided"]:
        expected = generate_expected_answer(
            question_text=question.text if question else "",
            keywords_list=[k.strip() for k in question.keywords.split(',')] if (question and question.keywords) else []
        )
        return {
            "score": 0,
            "feedback": "You did not provide an answer to this question.",
            "improvement_tips": [
                "Review the expected answer below to learn key concepts for this question",
                "Try answering the question in your own words next time",
                "Explain the main idea clearly with practical examples"
            ],
            "expected_answer": expected,
            "resume_grounding": None,
        }

    # ---------- INTERNAL SCORING (HIDDEN FROM USER) ----------
    doc = nlp(text)
    tokens = [t.text.lower() for t in doc]

    fillers = sum(1 for t in tokens if t in FILLERS)
    word_count = len(text.split())

    keywords = []
    matched = 0
    if question and question.keywords:
        keywords = [k.strip().lower() for k in question.keywords.split(',') if k.strip()]
        matched = sum(1 for k in keywords if k in text.lower())

    # Shared metrics:
    # Length Score (0–15 points)
    length_score = min(15, max(3, word_count // 2))

    # Fluency/Filler Score (0–20 points) - subtracts 4 points per filler word
    fluency_score = max(0, 20 - (fillers * 4))

    resume_grounding = None
    question_text = question.text if question else ""

    # Check if this is a Resume-backed session with a valid resume object
    if resume and getattr(resume, 'id', None):
        try:
            from .rag.resume_rag import retrieve_resume_context_for_answer
            chunks = retrieve_resume_context_for_answer(
                resume_obj=resume,
                question_text=question_text,
                answer_text=text,
                top_k=3,
            )
            if chunks:
                grounded_result = evaluate_resume_grounded_answer(
                    question_text=question_text,
                    answer_text=text,
                    keywords_list=keywords,
                    resume_chunks=chunks,
                    job_description=job_description,
                )
                if grounded_result:
                    correctness_score = grounded_result["correctness_score"]  # 0–45
                    consistency_score = grounded_result["consistency_score"]  # 0–20
                    total_score = max(0, min(100, correctness_score + consistency_score + length_score + fluency_score))
                    resume_grounding = grounded_result
        except Exception as exc:
            import logging
            logging.getLogger(__name__).warning("Resume grounding failed; falling back to standard: %s", exc)

    # Standard / Non-Resume scoring fallback (65 / 15 / 20)
    if resume_grounding is None:
        correctness_score = evaluate_semantic_correctness(
            question_text=question_text,
            answer_text=text,
            keywords_list=keywords,
        )
        # Fallback to keyword-based score scaled to 65 if LLM call fails
        if correctness_score < 0:
            correctness_score = int((matched / max(1, len(keywords))) * 65) if keywords else 32

        total_score = max(0, min(100, correctness_score + length_score + fluency_score))

    # ---------- AI-GENERATED FEEDBACK ----------
    ai_feedback = generate_ai_answer_feedback(
        question_text=question_text,
        answer_text=text,
        score=total_score,
        resume_grounding=resume_grounding,
    )

    # Safety fallback (AI failure or invalid structure)
    if not isinstance(ai_feedback, dict) or "feedback" not in ai_feedback:
        ai_feedback = {
            "feedback": "Your answer addresses the question but could be explained more clearly.",
            "improvement_tips": [
                "Structure your answer step by step",
                "Add a concrete example",
                "Explain why the concept is important"
            ]
        }

    return {
        "score": int(total_score),
        "feedback": ai_feedback.get("feedback", "Your answer was recorded."),
        "improvement_tips": ai_feedback.get("improvement_tips", []),
        "resume_grounding": resume_grounding,
    }


def generate_ai_answer_feedback(question_text, answer_text, score, resume_grounding=None):
    resume_clause = ""
    if resume_grounding:
        missed = resume_grounding.get("missed_resume_points", [])
        contra = resume_grounding.get("contradictions", [])
        supp = resume_grounding.get("supported_claims", [])
        
        notes = []
        if supp:
            notes.append(f"- Verified resume claims: {', '.join(supp)}")
        if missed:
            notes.append(f"- Resume details candidate omitted from answer: {', '.join(missed)}")
        if contra:
            notes.append(f"- Discrepancies vs resume: {', '.join(contra)}")
        if notes:
            resume_clause = "\nResume Verification Insights:\n" + "\n".join(notes) + "\nIncorporate coaching advice addressing these resume highlights or omissions naturally."

    prompt = f"""
You are an expert interview coach.

Question:
{question_text}

Candidate Answer:
{answer_text}

Internal Score: {score}/100
{resume_clause}

TASK:
Generate clear, human-friendly feedback for the candidate.

RULES:
- Do NOT mention scores, percentages, points, or keyword counts
- Do NOT sound robotic or academic
- Use simple language the candidate can understand
- Explain what was done well or poorly
- Give 3–5 specific, actionable improvement tips
- Tone should be encouraging and professional

Return ONLY valid JSON in this format:

{{
  "feedback": "Short paragraph explaining the quality of the answer",
  "improvement_tips": [
    "Tip 1",
    "Tip 2",
    "Tip 3"
  ]
}}
"""

    try:
        response = _call_groq_chat(prompt)
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end > start:
            return json.loads(response[start:end+1])
    except Exception:
        return None
