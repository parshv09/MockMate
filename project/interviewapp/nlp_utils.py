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

def analyze_transcript(text, question):
    if not text:
        return {
            "score": 0,
            "feedback": "You did not provide an answer to this question.",
            "improvement_tips": [
                "Answer the question in your own words",
                "Explain the main idea clearly",
                "Add an example to support your explanation"
            ]
        }

    doc = nlp(text)
    tokens = [t.text.lower() for t in doc]

    fillers = sum(1 for t in tokens if t in FILLERS)

    keywords = []
    matched = 0
    if question and question.keywords:
        keywords = [k.strip().lower() for k in question.keywords.split(',') if k.strip()]
        matched = sum(1 for k in keywords if k in text.lower())

    # ---- SCORING (internal) ----
    keyword_score = int((matched / max(1, len(keywords))) * 40) if keywords else 20
    length_score = min(20, max(5, len(text.split())))
    grammar_score = 25 - min(10, fillers * 2)
    filler_penalty = min(15, fillers * 3)
    total = max(0, keyword_score + length_score + grammar_score - filler_penalty)

    # ---- USER-FRIENDLY FEEDBACK ----
    word_count = len(text.split())
    feedback_parts = []

    if word_count < 12:
        feedback_parts.append(
            "Your answer is very short and does not fully explain the concept."
        )
    elif word_count < 25:
        feedback_parts.append(
            "Your answer explains the idea briefly, but it needs more depth."
        )
    else:
        feedback_parts.append(
            "You have explained the concept reasonably well."
        )

    if keywords and matched == 0:
        feedback_parts.append(
            "Important points related to the question are missing."
        )
    elif keywords and matched < len(keywords):
        feedback_parts.append(
            "Some important aspects of the topic are missing from your explanation."
        )

    if fillers > 0:
        feedback_parts.append(
            "Try to reduce filler words to make your answer clearer and more confident."
        )

    feedback = " ".join(feedback_parts)

    # ---- RULE-BASED FALLBACK TIPS ----
    rule_tips = []
    if word_count < 25:
        rule_tips.append("Explain the concept in 2–3 clear sentences")
    if keywords and matched < len(keywords):
        rule_tips.append("Include definition, purpose, and usage")
    rule_tips.append("Add a simple real-world or technical example")

    # ---- AI-GENERATED TIPS ----
    ai_tips = generate_ai_improvement_tips(
        answer_text=text,
        question_text=question.text if question else "",
        score=int(total)
    )

    improvement_tips = ai_tips if ai_tips else rule_tips

    return {
        "score": int(total),
        "feedback": feedback,
        "improvement_tips": improvement_tips
    }
