# interviewapp/qgen_groq.py
import os
import json
import time
import hashlib
import logging
import requests

from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE = "https://api.groq.com/openai/v1"  # Groq exposes OpenAI-compatible endpoints
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")  # change if needed

MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # seconds

def signature_of_text(text: str) -> str:
    norm = " ".join(text.lower().split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

def _build_prompt(role: str, n: int, difficulty: int = 3) -> str:
    return f"""
You are an interview question generator.

Generate exactly {n} unique interview questions for role = "{role}" with difficulty level {difficulty}.
Return only a JSON array (and nothing else). Each array item must be an object with keys:
- "text": string - the question text (short, clear, <=250 chars)
- "keywords": string - comma-separated keywords the candidate should ideally include
- "difficulty": integer 1-5

Rules:
1) Return ONLY a JSON array (no commentary).
2) Avoid PII, names, or confidential info.
3) Ensure each question is unique.
4) Keep questions practical and answerable in 1-2 minutes.
5) Ensure safe/clean content.

Example:
[
  {{"text":"Explain the difference between process and thread with an example.","keywords":"process,thread,concurrency,context-switch","difficulty":3}},
  {{"text":"Design a simple REST API for a library catalog and list key endpoints.","keywords":"API,REST,CRUD,authentication","difficulty":4}}
]
"""

def _call_groq_chat(prompt: str, model: Optional[str] = None) -> str:
    """
    Call Groq Chat Completions (OpenAI-compatible endpoint).
    Returns the model text output (string).
    """
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set in environment")

    model = model or GROQ_MODEL
    url = f"{GROQ_BASE}/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are an interview question generator."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 700,
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(url, headers=headers, json=body, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            # Groq returns OpenAI-compatible response shape:
            # data["choices"][0]["message"]["content"]
            content = None
            if "choices" in data and data["choices"]:
                message = data["choices"][0].get("message") or data["choices"][0]
                content = message.get("content") if isinstance(message, dict) else str(message)
            elif "output" in data:  # some variants
                content = data["output"][0]["content"][0]["text"]
            else:
                content = json.dumps(data)
            return content
        except requests.RequestException as e:
            logger.warning("Groq request failed (attempt %s): %s", attempt, e)
            if attempt == MAX_RETRIES:
                raise
            time.sleep(RETRY_BACKOFF * attempt)
    raise RuntimeError("Groq call failed after retries")

def _extract_json_array_from_text(text: str) -> List[Dict]:
    """Find the first JSON array in text and parse it."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in model output")
    raw = text[start:end+1]
    parsed = json.loads(raw)
    if not isinstance(parsed, list):
        raise ValueError("Parsed JSON is not a list")
    return parsed

def _validate_question_obj(obj: dict) -> Optional[dict]:
    if not isinstance(obj, dict):
        return None
    text = obj.get("text")
    keywords = obj.get("keywords", "")
    difficulty = obj.get("difficulty", 3)
    if not text or not isinstance(text, str):
        return None
    try:
        difficulty = int(difficulty)
        if difficulty < 1 or difficulty > 5:
            difficulty = max(1, min(5, difficulty))
    except:
        difficulty = 3
    if isinstance(keywords, list):
        keywords = ",".join(str(k).strip() for k in keywords if k)
    else:
        keywords = str(keywords).strip()
    return {"text": text.strip(), "keywords": keywords, "difficulty": difficulty}

def generate_questions_groq(role: str, n: int = 5, difficulty: int = 3, model: Optional[str] = None) -> List[dict]:
    """
    Generate up to n validated question dicts by calling Groq.
    Returns list of dict: {'text','keywords','difficulty'}.
    May raise exceptions on network/parse failures.
    """
    prompt = _build_prompt(role, n, difficulty)
    out = _call_groq_chat(prompt, model=model)
    parsed = _extract_json_array_from_text(out)
    validated = []
    for obj in parsed:
        v = _validate_question_obj(obj)
        if v:
            validated.append(v)
            if len(validated) >= n:
                break
    if not validated:
        raise ValueError("No valid questions parsed from Groq output")
    return validated
