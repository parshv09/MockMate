import json
from interviewapp.qgen_groq import _call_groq_chat

def generate_video_behavior_feedback(
    role,
    confidence_score,
    presence_pct,
    eye_contact_pct,
    movement_pct
):
    prompt = f"""
You are an expert interview coach.

Interview Role: {role}

Video Behavior Metrics:
- Overall Confidence Score: {confidence_score}/100
- Camera Presence: {presence_pct}%
- Eye Contact: {eye_contact_pct}%
- Head Movement: {movement_pct}%

TASK:
Generate clear, friendly, human-understandable feedback for the candidate.

RULES:
- Do NOT mention percentages explicitly.
- Do NOT sound robotic.
- Do NOT list raw metrics.
- Explain strengths and areas to improve.
- Give 3–5 actionable improvement tips.
- Tone should be encouraging, like a real interviewer.

Return ONLY valid JSON in this format:

{{
  "summary": "Short paragraph summarizing overall confidence",
  "strengths": ["strength 1", "strength 2"],
  "improvements": ["improvement 1", "improvement 2"],
  "tips": ["tip 1", "tip 2", "tip 3"]
}}
"""

    try:
        response = _call_groq_chat(prompt, model="llama-3.1-8b-instant")
        start = response.find("{")
        end = response.rfind("}")
        return json.loads(response[start:end+1])
    except Exception:
        return None
