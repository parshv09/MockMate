# interviewapp/qgen_groq.py  (FULL REPLACEMENT)
import os
import json
import time
import hashlib
import logging
import requests
import re
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

_NUMERIC_RE = re.compile(r'[-+]?\d[\d,]*(?:\.\d+)?')  # detect numbers, currency, etc.

# Role normalizer and preferences (tune as you like)
def _normalize_role_key(role: str) -> str:
    if not role:
        return "default"
    r = role.lower()
    if "tech" in r or "technical" in r:
        return "technical"
    if "apt" in r or "aptitude" in r:
        return "aptitude"
    if "hr" in r or "human" in r:
        return "hr"
    if "beh" in r or "behavior" in r:
        return "beh"
    return "default"

# desired math ratio per role (0.0 .. 1.0)
ROLE_MATH_RATIO = {
    "aptitude": 0.5,
    "technical": 0.05,  # almost no math for technical role by default
    "hr": 0.0,
    "beh": 0.0,
    "default": 0.4
}

# allowed types per role
ROLE_ALLOWED_TYPES = {
    "aptitude": {"math", "reasoning"},
    "technical": {"reasoning"},  # strictly reasoning (no numeric/math)
    "hr": {"reasoning"},
    "beh": {"reasoning"},
    "default": {"math", "reasoning"},
}

def signature_of_text(text: str) -> str:
    norm = " ".join(text.lower().split())
    return hashlib.sha256(norm.encode("utf-8")).hexdigest()

def _is_math_question_textual(text: str) -> bool:
    if not text:
        return False
    t = str(text).lower()
    if _NUMERIC_RE.search(t):
        return True
    if "%" in t or "$" in t or "₹" in t or "rupee" in t:
        return True
    math_words = ("calculate", "compute", "probability", "percent", "ratio", "sum", "difference",
                  "distance", "speed", "time", "how many", "what is the next number", "series",
                  "expected value", "mean", "median", "mode")
    if any(w in t for w in math_words):
        return True
    return False

def _build_prompt(role: str, n: int, difficulty: int = 3, math_needed: int = 0) -> str:
    """
    Build a JSON-only prompt. If math_needed > 0 we require that many math items in this batch.
    If math_needed == 0, request zero math items.
    """
    math_clause = ""
    if math_needed > 0:
        math_clause = f"- Exactly {math_needed} of the {n} items MUST be of type \"math\" and include numeric data.\n"
    else:
        math_clause = f"- ZERO items of the {n} items should be of type \"math\".\n"

    return f"""
You are a careful interview question generator.

TASK:
Generate EXACTLY {n} unique interview questions for the role "{role}" and difficulty {difficulty}.
Return ONLY a JSON array. Each entry MUST be an object with keys:
  - "text": string - the question text (≤ 300 chars). For math questions include numeric data and a clear ask.
  - "keywords": string - comma-separated keywords.
  - "difficulty": integer 1-5.
  - "type": string - either "math" or "reasoning".

MIX RULE:
{math_clause}
- The rest of the items must be of type "reasoning".
- Ensure variety: do not repeat same template or numeric values.
- If you cannot meet constraints, return an empty array [].

FORMAT RULES:
- RETURN ONLY the JSON array and NOTHING ELSE (no commentary, no markdown).
- Ensure valid JSON (double quotes, no trailing commas).

Examples:
[
  {{"text":"A machine produces 120 parts in 8 hours. At the same rate how many parts in 5 hours?","keywords":"rate,proportion","difficulty":2,"type":"math"}},
  {{"text":"Describe a time you handled conflicting priorities and how you decided.","keywords":"prioritization,tradeoffs","difficulty":3,"type":"reasoning"}}
]

CONSTRAINTS:
- Avoid PII or offensive content.
- Keep questions clear and answerable within 1-5 minutes.
"""

def _call_groq_chat(prompt: str, model: Optional[str] = None, temperature: float = 0.15) -> str:
    if not GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY not set")
    url = f"{GROQ_BASE}/chat/completions"
    body = {
        "model": model or GROQ_MODEL,
        "messages": [
            {"role": "system", "content": "You are an interview question generator."},
            {"role": "user", "content": prompt}
        ],
        "temperature": temperature,
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
    """
    Validate basic fields and ensure a 'type' is present (infer if missing).
    Returns normalized dict with keys: text, keywords, difficulty, type
    """
    if not isinstance(obj, dict):
        return None
    text = obj.get("text")
    keywords = obj.get("keywords", "")
    difficulty = obj.get("difficulty", 3)
    qtype = obj.get("type", "").lower() if obj.get("type") else ""
    if not text or not isinstance(text, str):
        return None
    try:
        difficulty = int(difficulty)
        difficulty = max(1, min(5, difficulty))
    except Exception:
        difficulty = 3
    # normalize keywords
    if isinstance(keywords, list):
        keywords = ",".join(str(k).strip() for k in keywords if k)
    else:
        keywords = str(keywords).strip()
    # infer type if missing or invalid
    if qtype not in ("math", "reasoning"):
        qtype = "math" if _is_math_question_textual(text) else "reasoning"
    return {"text": text.strip(), "keywords": keywords, "difficulty": difficulty, "type": qtype}

def _ensure_math_has_number(qobj: dict) -> dict:
    """
    Ensure math-type questions have numeric content. If 'type' == 'math' but text lacks numbers,
    attempt to enrich by appending a small numeric example.
    """
    text = qobj.get("text", "").strip()
    qtype = qobj.get("type", "").lower()
    if qtype == "math":
        if not _NUMERIC_RE.search(text):
            enrich = " For example: If 10 items cost 25, how much for 4?"
            qobj["text"] = (text + enrich)[:1000]
            if qobj.get("keywords"):
                qobj["keywords"] += ",numbers"
            else:
                qobj["keywords"] = "numbers"
    # normalize difficulty and keywords already done in _validate
    return qobj

def _is_math_question(qobj: dict) -> bool:
    """
    Heuristic to decide if a validated question is math.
    Checks declared type and textual numeric cues.
    """
    if not isinstance(qobj, dict):
        return False
    if qobj.get("type") == "math":
        return True
    return _is_math_question_textual(qobj.get("text", ""))

def enforce_role_allowed_types(role_key: str, collected: list, n: int, difficulty: int = 3, model: Optional[str] = None) -> list:
    """
    Remove disallowed types for the role and try to replace them by targeted LLM calls.
    Returns a list (<= n) of allowed items.
    """
    allowed = ROLE_ALLOWED_TYPES.get(role_key, ROLE_ALLOWED_TYPES["default"])
    kept = []
    removed_slots = 0

    # keep items allowed, remove disallowed
    for q in collected:
        if _is_math_question(q) and "math" not in allowed:
            removed_slots += 1
            continue
        kept.append(q)

    attempts = 0
    max_attempts = max(2, removed_slots * 3)

    while removed_slots > 0 and attempts < max_attempts:
        attempts += 1
        # request exactly removed_slots items with math_needed=0 (i.e., only reasoning)
        prompt = _build_prompt(role=role_key.capitalize(), n=removed_slots, difficulty=difficulty, math_needed=0)
        try:
            out = _call_groq_chat(prompt, model=model)
            parsed = _extract_json_array_from_text(out)
        except Exception as e:
            logger.exception("Replacement call failed: %s", e)
            break

        for obj in parsed:
            v = _validate_question_obj(obj)
            if not v:
                continue
            # skip math if still returned erroneously
            if _is_math_question(v) and "math" not in allowed:
                continue
            v = _ensure_math_has_number(v)
            kept.append(v)
            removed_slots -= 1
            if removed_slots <= 0:
                break

    return kept[:n]

def generate_questions_groq(role: str, n: int = 5, difficulty: int = 3, model: Optional[str] = None) -> List[dict]:
    """
    Generate up to n validated question dicts with role-aware math/reasoning constraints.
    """
    role_key = _normalize_role_key(role)
    math_ratio = ROLE_MATH_RATIO.get(role_key, ROLE_MATH_RATIO["default"])
    math_needed_total = max(0, int(round(n * math_ratio)))

    collected = []
    seen_sigs = set()
    attempts = 0
    max_attempts = max(3, n * 3)
    math_count = 0

    while len(collected) < n and attempts < max_attempts:
        attempts += 1
        remaining = n - len(collected)
        # compute how many math we still need overall and in this batch
        math_needed_remaining = max(0, math_needed_total - math_count)
        math_for_this_call = min(remaining, math_needed_remaining)

        # build prompt asking for remaining questions and math quota for this call
        prompt = _build_prompt(role=role.capitalize(), n=remaining, difficulty=difficulty, math_needed=math_for_this_call)

        try:
            out = _call_groq_chat(prompt, model=model, temperature=0.2)
        except Exception as e:
            logger.exception("Groq call failed: %s", e)
            break

        try:
            parsed = _extract_json_array_from_text(out)
        except Exception as e:
            logger.exception("JSON extraction failed: %s", e)
            continue

        for obj in parsed:
            v = _validate_question_obj(obj)
            if not v:
                continue
            v = _ensure_math_has_number(v)
            sig = signature_of_text(v["text"])
            if sig in seen_sigs:
                continue
            seen_sigs.add(sig)
            collected.append(v)
            if v.get("type") == "math":
                math_count += 1
            if len(collected) >= n:
                break

        # If we have filled slots but math_count < math_needed_total, remove some reasoning to make room
        if len(collected) >= n and math_count < math_needed_total:
            to_remove = math_needed_total - math_count
            filtered = []
            removed = 0
            for q in collected:
                if q.get("type") != "math" and removed < to_remove:
                    removed += 1
                    continue
                filtered.append(q)
            collected = filtered
            math_count = len([q for q in collected if q.get("type") == "math"])
            seen_sigs = set(signature_of_text(q["text"]) for q in collected)

    # Final enforcement: remove disallowed types and attempt targeted replacements if needed
    final = collected[:n]
    final = enforce_role_allowed_types(role_key, final, n, difficulty=difficulty, model=model)

    # If still fewer than n, fill with safe stubs
    if len(final) < n:
        missing = n - len(final)
        logger.info("Filling %s missing questions with stubs", missing)
        from .views_helpers import generate_question_stub  # import here to avoid circular import at module load
        for _ in range(missing):
            stub = generate_question_stub(role_key, difficulty=difficulty)
            # ensure uniqueness vs seen_sigs
            sig = signature_of_text(stub.get("text", ""))
            if sig in seen_sigs and not DEV_FORCE_CREATE:
                # try small mutation by appending index phrase (dev-only)
                stub_text = stub["text"] + " (variant)"
                stub["text"] = stub_text
                sig = signature_of_text(stub_text)
            seen_sigs.add(sig)
            final.append({
                "text": stub.get("text", "").strip(),
                "keywords": stub.get("keywords", ""),
                "difficulty": stub.get("difficulty", 3),
                "type": "math" if _is_math_question_textual(stub.get("text", "")) else "reasoning"
            })

    # Trim to exactly n and return
    return final[:n]

# in interviewapp/qgen_groq.py (append)
# qgen_groq.py (append this) — compact safe version
def generate_session_suggestions(session, answers: List[dict], model: Optional[str]=None) -> dict:
    """
    answers: list of dicts {question_text, answer_text, score, feedback}
    Returns dict: strengths, improvements, overall_tip, resources
    """
    # Prepare small JSON of Q/A pairs (truncate to avoid huge prompts)
    items = []
    for a in answers:
        q = (a.get("question_text") or "")[:600].replace("\n", " ")
        ans = (a.get("answer_text") or "")[:1000].replace("\n", " ")
        items.append({"q": q, "a": ans, "score": a.get("score", 0), "fb": (a.get("feedback") or "")[:300]})
    items_json = json.dumps(items, ensure_ascii=False)[:22000]

    prompt = f"""
You are an expert interview coach. Given the following list of question/answer/score/feedback items, produce ONLY a JSON object:
{{"strengths":[...], "improvements":[...], "overall_tip":"...", "resources":[...]}}

Input:
{items_json}

Rules:
- strengths: 2-4 short bullets of what the candidate did well.
- improvements: 3-6 actionable bullets (specific steps).
- overall_tip: one concise paragraph.
- resources: 3-6 suggestions (books, websites, courses).
Return valid JSON only.
"""
    try:
        out = _call_groq_chat(prompt, model=model, temperature=0.2)
        # extract first JSON object in response
        start = out.find("{")
        end = out.rfind("}")
        if start == -1:
            raise ValueError("No JSON in LLM response")
        raw = out[start:end+1]
        parsed = json.loads(raw)
        # normalize keys
        return {
            "strengths": parsed.get("strengths", []),
            "improvements": parsed.get("improvements", []),
            "overall_tip": parsed.get("overall_tip", ""),
            "resources": parsed.get("resources", [])
        }
    except Exception as e:
        logging.getLogger(__name__).exception("LLM suggestions failed: %s", e)
        # fallback simple heuristic
        strengths = []
        improvements = []
        for a in sorted(answers, key=lambda x: x.get("score", 0), reverse=True)[:3]:
            strengths.append(a.get("question_text","")[:120])
        for a in sorted(answers, key=lambda x: x.get("score", 0))[:5]:
            improvements.append(a.get("question_text","")[:120])
        return {
            "strengths": strengths,
            "improvements": improvements,
            "overall_tip": "Practice weaker areas identified above; do timed mock interviews and focus on concise structure.",
            "resources": ["LeetCode", "Cracking the Coding Interview", "Grokking the System Design Interview"]
        }
