# interviewapp/qgen_groq.py  (REPLACE file contents with this)
import os
import json
import time
import hashlib
import logging
import requests
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_BASE = "https://api.groq.com/openai/v1"
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

MAX_RETRIES = 4
RETRY_BACKOFF = 1.5
CALL_TIMEOUT = 60  # seconds
DEV_FORCE_CREATE = bool(os.getenv("DEV_FORCE_CREATE", False))  # set "True" in .env to force-create during dev

def signature_of_text(text: str) -> str:
    norm = " ".join(text.lower().split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

def _build_prompt(role: str, n: int, difficulty: int = 3) -> str:
    # role should be a readable string like "Technical (Frontend)" or "HR"
    return f"""
You are a strict JSON-only interview question generator.

TASK:
Generate a JSON ARRAY with exactly {n} items. Each item MUST be an object with keys:
  - "text": short question (<=250 chars), directly the question content (no numbering, no prefixes)
  - "keywords": comma-separated keywords that a good answer should include (short phrases)
  - "difficulty": integer 1-5

ROLE:
The role is: "{role}"
DIFFICULTY: {difficulty}

CONSTRAINTS:
- RETURN ONLY the JSON ARRAY and NOTHING ELSE (no prose, no explanations, no code fences).
- Ensure each question is UNIQUE and relevant to the role.
- Avoid PII, names, or offensive content.
- If you cannot produce the array exactly, return an empty array: [].
"""

def _call_groq_chat(prompt: str, model: Optional[str] = None) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    url = f"{GROQ_BASE}/chat/completions"
    body = {
        "model": model or GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are an interview question generator."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,   # deterministic
        "max_tokens": 1000,
        "top_p": 0.95,
    }
    headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Groq call attempt %s model=%s", attempt, body["model"])
            resp = requests.post(url, headers=headers, json=body, timeout=CALL_TIMEOUT)
            status = getattr(resp, "status_code", None)
            text = resp.text or ""
            logger.info("Groq status %s (len=%s)", status, len(text))
            # save raw response for debugging
            try:
                with open("groq_last_response.txt", "w", encoding="utf-8") as f:
                    f.write(f"STATUS:{status}\n")
                    f.write(text)
            except Exception:
                logger.exception("Failed to write groq_last_response.txt")

            # try to extract content in common shapes
            try:
                data = resp.json()
            except Exception:
                data = None

            content = None
            if data and "choices" in data and data["choices"]:
                # OpenAI-compatible
                ch = data["choices"][0]
                message = ch.get("message") or ch
                if isinstance(message, dict):
                    content = message.get("content") or message.get("text")
                else:
                    content = str(message)
            elif data and "output" in data:
                try:
                    content = data["output"][0]["content"][0]["text"]
                except Exception:
                    content = str(data)
            else:
                content = text

            if not content:
                raise RuntimeError("Empty content returned by Groq")
            return content
        except Exception as e:
            last_exc = e
            logger.exception("Groq call failed (attempt %s): %s", attempt, e)
            time.sleep(RETRY_BACKOFF * attempt)
    raise last_exc or RuntimeError("Groq call failed after retries")

def _extract_json_array_from_text(text: str) -> List[Dict]:
    """
    Find the first JSON array (outermost) and parse it. Raise a helpful error if not found/valid.
    """
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end <= start:
        logger.warning("No JSON array found in model text. Snippet: %s", text[:1000])
        raise ValueError("No JSON array found in model output; see groq_last_response.txt")
    raw = text[start:end+1]
    try:
        parsed = json.loads(raw)
    except Exception as e:
        logger.exception("JSON parse error for raw (len=%s): %s", len(raw), e)
        raise
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
        difficulty = max(1, min(5, difficulty))
    except Exception:
        difficulty = 3
    if isinstance(keywords, list):
        keywords = ",".join(str(k).strip() for k in keywords if k)
    else:
        keywords = str(keywords).strip()
    return {"text": text.strip(), "keywords": keywords, "difficulty": difficulty}

def generate_questions_groq(role: str, n: int = 5, difficulty: int = 3, model: Optional[str] = None) -> List[dict]:
    """
    Generate exactly n unique, validated question dicts (if possible).
    Will attempt multiple calls and collect unique signatures until n or until attempt cap.
    """
    collected = []
    seen_sigs = set()
    attempts = 0
    max_total_attempts = max(3, n * 2)  # try up to this many model calls

    while len(collected) < n and attempts < max_total_attempts:
        attempts += 1
        prompt = _build_prompt(role, n - len(collected), difficulty)
        try:
            out = _call_groq_chat(prompt, model=model)
        except Exception as e:
            logger.exception("LLM call failed on attempt %s: %s", attempts, e)
            # break to let fallback happen in caller
            break
        # attempt parse
        try:
            parsed = _extract_json_array_from_text(out)
        except Exception as e:
            logger.exception("Failed to parse LLM output on attempt %s: %s", attempts, e)
            # try one more attempt
            continue

        # validate and collect (unique by signature)
        for obj in parsed:
            v = _validate_question_obj(obj)
            if not v:
                continue
            sig = signature_of_text(v["text"])
            if sig in seen_sigs:
                continue
            seen_sigs.add(sig)
            collected.append(v)
            if len(collected) >= n:
                break

    # final check: may return fewer than n; caller should fallback if needed
    return collected
