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
        response = _call_groq_chat(prompt, model="llama-3.1-8b-instant")
        start = response.find("[")
        end = response.rfind("]")
        tips = json.loads(response[start:end+1])
        if isinstance(tips, list):
            return tips[:5]
    except Exception:
        pass

    return []

def evaluate_semantic_correctness(question_text, answer_text, keywords_list):
    """
    Evaluate the correctness and completeness of the candidate's answer using Groq LLM.
    Returns a score out of 60.
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
Rate the answer on a scale of 0 to 60 points based on its factual correctness and relevance:
- 50–60: Excellent, highly accurate, complete, and covers key concepts.
- 35–49: Good, mostly correct, covers the main points but lacks minor detail.
- 20–34: Average/Partial, has correct ideas but is shallow, incomplete, or slightly off-topic.
- 1–19: Poor, highly inaccurate, or barely relevant.
- 0: Completely incorrect, irrelevant, or empty.

Return ONLY valid JSON in this format:
{{
  "correctness_score": <integer score between 0 and 60>
}}
"""
    try:
        response = _call_groq_chat(prompt, model="llama-3.1-8b-instant")
        start = response.find("{")
        end = response.rfind("}")
        data = json.loads(response[start:end+1])
        score = int(data.get("correctness_score", 0))
        return max(0, min(60, score))
    except Exception:
        # Fallback code will handle if -1 is returned
        return -1


def analyze_transcript(text, question):
    # ---------- CASE: NO ANSWER ----------
    if not text:
        return {
            "score": 0,
            "feedback": "You did not provide an answer to this question.",
            "improvement_tips": [
                "Try answering the question in your own words",
                "Explain the main idea clearly",
                "Add a simple example to support your answer"
            ]
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

    # 1. Correctness Score (0–60 points) via LLM
    correctness_score = evaluate_semantic_correctness(
        question_text=question.text if question else "",
        answer_text=text,
        keywords_list=keywords
    )

    # Fallback to keyword-based score scaled to 60 if LLM call fails
    if correctness_score < 0:
        correctness_score = int((matched / max(1, len(keywords))) * 60) if keywords else 30

    # 2. Length Score (0–15 points) - scales gradually
    length_score = min(15, max(3, word_count // 2))

    # 3. Fluency/Filler Score (0–25 points) - subtracts 5 points per filler word
    fluency_score = max(0, 25 - (fillers * 5))

    total_score = max(0, min(100, correctness_score + length_score + fluency_score))

    # ---------- AI-GENERATED FEEDBACK ----------
    ai_feedback = generate_ai_answer_feedback(
        question_text=question.text if question else "",
        answer_text=text,
        score=total_score
    )

    # Safety fallback (AI failure)
    if not ai_feedback:
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
        "feedback": ai_feedback["feedback"],
        "improvement_tips": ai_feedback["improvement_tips"]
    }


def generate_ai_answer_feedback(question_text, answer_text, score):
    prompt = f"""
You are an expert interview coach.

Question:
{question_text}

Candidate Answer:
{answer_text}

Internal Score: {score}/100

TASK:
Generate clear, human-friendly feedback for the candidate.

RULES:
- Do NOT mention scores, percentages, or keyword counts
- Do NOT sound robotic or academic
- Use simple language the candidate can understand
- Explain what was done well or poorly
- Give 3–5 specific improvement tips
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
        response = _call_groq_chat(prompt, model="llama-3.1-8b-instant")
        start = response.find("{")
        end = response.rfind("}")
        return json.loads(response[start:end+1])
    except Exception:
        return None
