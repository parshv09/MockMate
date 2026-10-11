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
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

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

def _build_prompt(role: str, job_role: str, n: int, difficulty: int = 2, math_needed: int = 0, previous_questions: list = None) -> str:
    """
    Build a JSON-only prompt tailored to the specified job_role and difficulty level.
    """
    math_clause = ""
    if math_needed > 0:
        math_clause = f"- Exactly {math_needed} of the {n} items MUST be of type \"math\" and include numeric data.\n"
    else:
        math_clause = f"- ZERO items of the {n} items should be of type \"math\".\n"

    # Define difficulty details
    diff_val = int(difficulty)
    if diff_val <= 2:
        diff_instruction = "The questions should be introductory, fundamental, and conceptual. Focus on basic definitions, syntax, simple operations, and core vocabulary suited for entry-level candidates or interns. Avoid complex architectural, design pattern, or optimization questions."
    elif diff_val <= 4:
        diff_instruction = "The questions should test practical development knowledge, intermediate concepts, problem-solving, and implementation details. Suit this for candidates with 2-4 years of experience. Ask about best practices, common libraries/frameworks, basic system design, and testing."
    else:
        diff_instruction = "The questions should be deep, complex, and highly technical. Focus on performance optimization, advanced architecture, concurrency, microservices, scaling challenges, low-level details, security, and trade-offs. Suit this for senior candidates with 5+ years of experience."

    # Define role-specific guidelines to ensure high-quality and realistic questions
    role_lower = role.lower()
    role_instructions = ""
    
    if "human resources" in role_lower or "hr" == role_lower:
        role_instructions = f"""
- These must be HR interview questions asked BY AN HR INTERVIEWER TO THE CANDIDATE who is applying for the job of {job_role}.
- Do NOT generate questions testing the candidate's ability to DO human resources work (e.g. no questions on how to hire, run payroll, or design company benefits).
- Instead, generate classic behavioral and fit questions asked of a {job_role} candidate (e.g., questions about career goals, strengths/weaknesses, teamwork, handling conflict, motivation, and why they want to join the company).
"""
    elif "technical" in role_lower or "tech" in role_lower:
        role_instructions = f"""
- Generate actual technical questions commonly asked in interviews for a {job_role} position.
- Focus on key technologies, programming concepts, architecture, syntax, tools, or domain-specific logic that a qualified {job_role} must know.
"""
    elif "behavioral" in role_lower or "beh" in role_lower:
        role_instructions = f"""
- Generate situational and behavioral questions asked of a candidate applying for the job of {job_role}.
- Focus on real-world scenarios: handling project deadlines, working in teams, resolving conflicts, learning from failures, or solving problems under pressure.
"""
    else:
        # Fallback or Aptitude
        role_instructions = f"""
- Generate questions appropriate for a candidate interviewing for a {job_role} position.
"""

    # Avoid previously asked questions
    avoid_clause = ""
    if previous_questions:
        avoid_clause = "\n- Do NOT generate any questions similar to the following previously asked questions:\n"
        for pq in previous_questions:
            avoid_clause += f"  * {pq}\n"

    return f"""
You are an expert interviewer. Generate EXACTLY {n} questions for a {role} interview round for a candidate applying for the job role: "{job_role}".

Difficulty Level / Target Depth:
{diff_instruction}

Rules:
{role_instructions}
- {math_clause}
{avoid_clause}
- Ask realistic, high-quality questions that are commonly asked in real-world interviews for this role.
- Keep questions clear, focused, and answerable within 5 minutes.
- Do NOT ask the candidate to write or develop long sections of code; ask conceptual or code-analysis questions instead.
- Generate unique, varied questions each time.
- Each item must include: text, keywords (comma-separated target terms candidate should mention), difficulty, type (either "math" or "reasoning").

Return ONLY a valid JSON array of objects in this exact format:
[
  {{
    "text": "The question text",
    "keywords": "keyword1,keyword2,keyword3",
    "difficulty": {difficulty},
    "type": "reasoning"
  }}
]
"""

def _get_groq_api_key() -> str:
    key = os.getenv("GROQ_API_KEY", "")
    if not key:
        try:
            from django.conf import settings
            key = getattr(settings, "GROQ_API_KEY", "")
        except Exception:
            pass
    return key or GROQ_API_KEY

def _call_groq_chat(prompt: str, model: Optional[str] = None, temperature: float = 0.15) -> str:
    api_key = _get_groq_api_key()
    if not api_key:
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
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    last_exc = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logger.info("Groq call attempt %s model=%s", attempt, body["model"])
            resp = requests.post(url, headers=headers, json=body, timeout=CALL_TIMEOUT)
            status = getattr(resp, "status_code", None)
            body_len = len(resp.text or "")
            logger.info("Groq status %s (len=%s)", status, body_len)

            if status != 200:
                raise RuntimeError(f"Groq API returned HTTP status {status}")

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
                    content = None
            elif data:
                content = None
            else:
                content = None

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
        logger.warning("No JSON array found in model output (len=%s)", len(text or ""))
        raise ValueError("No JSON array found in model output")
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

def enforce_role_allowed_types(role_key: str, job_role: str, collected: list, n: int, difficulty: int = 3, previous_questions: list = None, model: Optional[str] = None) -> list:
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
        prompt = _build_prompt(role=role_key.capitalize(), job_role=job_role, n=removed_slots, difficulty=difficulty, math_needed=0, previous_questions=previous_questions)
        try:
            # Use temperature=0.7 for replacements as well to ensure diversity
            out = _call_groq_chat(prompt, model=model, temperature=0.7)
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

def generate_questions_groq(role: str, job_role: str, n: int = 5, difficulty: int = 3, previous_questions: list = None, model: Optional[str] = None) -> List[dict]:
    """
    Generate up to n validated question dicts with role-aware math/reasoning constraints, 
    avoiding previous questions and adhering to the difficulty level.
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
        prompt = _build_prompt(role=role.capitalize(), job_role=job_role, n=remaining, difficulty=difficulty, math_needed=math_for_this_call, previous_questions=previous_questions)

        try:
            # Set temperature to 0.7 to guarantee high variety and avoid repetitions
            out = _call_groq_chat(prompt, model=model, temperature=0.7)
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
    final = enforce_role_allowed_types(role_key, job_role, final, n, difficulty=difficulty, previous_questions=previous_questions, model=model)

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


DEFAULT_ROADMAPS = {
    "full-stack": {
        "title": "Full-Stack Developer Roadmap",
        "description": "Master end-to-end web development from frontend user interfaces to scalable backend APIs and databases.",
        "estimated_duration": "4 - 6 Months",
        "phases": [
            {
                "phase_number": 1,
                "title": "Frontend Core & Responsive UI",
                "duration": "4 Weeks",
                "summary": "Build responsive, accessible modern web interfaces using HTML5, CSS3, JavaScript (ES6+), and React.",
                "topics": ["Semantic HTML & Accessibility (a11y)", "CSS Layouts (Flexbox, Grid, Responsive Design)", "Modern JavaScript (ES6+, Async/Await, DOM)", "React Fundamentals & Hooks (useState, useEffect)", "State Management & Component Architecture"],
                "recommended_project": "Interactive Web Dashboard with live API data fetching & dark mode",
                "interview_focus": "DOM manipulation, closures, event delegation, React lifecycle, and CSS layout algorithms."
            },
            {
                "phase_number": 2,
                "title": "Backend APIs & Databases",
                "duration": "5 Weeks",
                "summary": "Design robust server-side APIs, database schemas, authentication, and backend architecture.",
                "topics": ["Node.js / Python Django / FastAPI", "RESTful API Design & Best Practices", "Relational Databases (PostgreSQL / MySQL)", "NoSQL & Caching (MongoDB, Redis)", "Authentication (JWT, OAuth2, Session Management)"],
                "recommended_project": "Multi-tenant REST API with JWT Auth, Role Permissions, and Database Indexing",
                "interview_focus": "SQL query optimization, database normalization, HTTP status codes, security best practices (CORS, XSS, CSRF)."
            },
            {
                "phase_number": 3,
                "title": "Full-Stack Integration & Testing",
                "duration": "4 Weeks",
                "summary": "Connect frontend and backend into a cohesive web application with automated unit and integration tests.",
                "topics": ["End-to-End State Management (Redux/Zustand)", "API Integration & Error Handling", "Unit Testing (Jest, PyTest)", "Integration & E2E Testing (Cypress / Playwright)", "Git Flow & CI/CD Pipelines"],
                "recommended_project": "E-Commerce App with Shopping Cart, Checkout, Webhooks, and Automated Test Suite",
                "interview_focus": "API pagination, optimistic UI updates, webhooks, error boundary strategies, and testing strategies."
            },
            {
                "phase_number": 4,
                "title": "System Design, DevOps & Deployment",
                "duration": "3 Weeks",
                "summary": "Deploy applications securely to cloud infrastructure with containerization and system design principles.",
                "topics": ["Docker & Containerization", "Cloud Hosting (AWS EC2/S3, Vercel, Render)", "Nginx Reverse Proxy & SSL Setup", "Basic System Design (Caching, Load Balancers, Queues)", "Performance Optimization (Lighthouse, CDN)"],
                "recommended_project": "Production Deployment of Full-Stack App with Automated Docker & GitHub Actions CI/CD",
                "interview_focus": "System architecture trade-offs, caching layers, microservices vs monolith, and performance tuning."
            }
        ]
    },
    "data-science": {
        "title": "Data Scientist & Analytics Roadmap",
        "description": "Master data manipulation, statistical analysis, machine learning models, and data visualization.",
        "estimated_duration": "5 - 7 Months",
        "phases": [
            {
                "phase_number": 1,
                "title": "Python & Data Wrangling Fundamentals",
                "duration": "4 Weeks",
                "summary": "Learn Python programming for data analysis, numerical computing, and data manipulation.",
                "topics": ["Python Foundations & Data Structures", "NumPy for Numerical Computation", "Pandas for Data Manipulation & Cleaning", "Exploratory Data Analysis (EDA)", "Data Visualization (Matplotlib, Seaborn)"],
                "recommended_project": "Exploratory Data Analysis on a Real-World Dataset (e.g. Airbnb or Financial Data)",
                "interview_focus": "Pandas indexing, vectorization vs loops, handling missing data, and outlier detection."
            },
            {
                "phase_number": 2,
                "title": "Applied Statistics & Probability",
                "duration": "4 Weeks",
                "summary": "Understand core statistical methods, hypothesis testing, distributions, and experiment design.",
                "topics": ["Descriptive & Inferential Statistics", "Probability Distributions & Bayes Theorem", "Hypothesis Testing & p-values", "A/B Testing Methodology", "Correlation & Regression Analysis"],
                "recommended_project": "Statistical A/B Testing Analysis for Product Feature Rollout",
                "interview_focus": "p-value interpretation, Central Limit Theorem, Type I/II errors, and sample size calculations."
            },
            {
                "phase_number": 3,
                "title": "Machine Learning Algorithms",
                "duration": "6 Weeks",
                "summary": "Train, evaluate, and fine-tune supervised and unsupervised machine learning algorithms using Scikit-Learn.",
                "topics": ["Supervised Learning (Linear/Logistic Regression, Decision Trees)", "Ensemble Methods (Random Forest, XGBoost)", "Unsupervised Learning (K-Means, PCA)", "Model Evaluation (Precision, Recall, ROC-AUC, F1)", "Feature Engineering & Hyperparameter Tuning"],
                "recommended_project": "Predictive ML Model (e.g. Customer Churn Prediction) with Scikit-Learn and MLflow",
                "interview_focus": "Bias-Variance trade-off, precision vs recall trade-offs, decision tree splitting criteria, and cross-validation."
            },
            {
                "phase_number": 4,
                "title": "Deep Learning & Model Deployment",
                "duration": "4 Weeks",
                "summary": "Build neural networks and deploy ML models into production as web APIs.",
                "topics": ["Neural Network Foundations (PyTorch / TensorFlow)", "Natural Language Processing (NLP) & Computer Vision Basics", "ML Model Deployment (FastAPI / Streamlit)", "Model Monitoring & Drift Detection", "SQL for Advanced Data Extraction"],
                "recommended_project": "Deploy an Interactive ML Web App on HuggingFace / Vercel with FastAPI backend",
                "interview_focus": "Model deployment lifecycle, handling imbalanced data, and neural network optimization algorithms."
            }
        ]
    }
}


def generate_ai_roadmap(role: str, experience_level: str = "Intermediate") -> dict:
    """
    Generate an interactive career and skill roadmap for any role.
    """
    role_key = (role or "full-stack").lower().replace(" ", "-")
    
    # Check pre-defined fallback roadmaps
    if role_key in DEFAULT_ROADMAPS:
        return DEFAULT_ROADMAPS[role_key]

    prompt = f"""
You are a principal tech career mentor and industry curriculum engineer.

Target Role: {role}
Target Level: {experience_level}

TASK:
Create a comprehensive, structured, highly practical career & skill learning roadmap for a candidate aiming to become a successful {role}.

Return ONLY a valid JSON object with the exact structure:
{{
  "title": "{role} Career Roadmap",
  "description": "Short 1-2 sentence overview of the career path.",
  "estimated_duration": "3 - 5 Months",
  "phases": [
    {{
      "phase_number": 1,
      "title": "Phase Title",
      "duration": "3-4 Weeks",
      "summary": "Short phase summary",
      "topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"],
      "recommended_project": "Bespoke project idea for this phase",
      "interview_focus": "Core interview topics and concepts tested at this stage"
    }},
    {{
      "phase_number": 2,
      "title": "Phase Title",
      "duration": "4 Weeks",
      "summary": "Short phase summary",
      "topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"],
      "recommended_project": "Bespoke project idea for this phase",
      "interview_focus": "Core interview topics and concepts tested at this stage"
    }},
    {{
      "phase_number": 3,
      "title": "Phase Title",
      "duration": "4 Weeks",
      "summary": "Short phase summary",
      "topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"],
      "recommended_project": "Bespoke project idea for this phase",
      "interview_focus": "Core interview topics and concepts tested at this stage"
    }},
    {{
      "phase_number": 4,
      "title": "Phase Title",
      "duration": "3 Weeks",
      "summary": "Short phase summary",
      "topics": ["Topic 1", "Topic 2", "Topic 3", "Topic 4", "Topic 5"],
      "recommended_project": "Bespoke project idea for this phase",
      "interview_focus": "Core interview topics and concepts tested at this stage"
    }}
  ]
}}
"""
    try:
        response = _call_groq_chat(prompt, temperature=0.2)
        start = response.find("{")
        end = response.rfind("}")
        if start != -1 and end > start:
            parsed = json.loads(response[start:end+1])
            if "phases" in parsed and isinstance(parsed["phases"], list):
                return parsed
    except Exception as e:
        logging.getLogger(__name__).exception("Failed to generate AI roadmap: %s", e)

    # Generic Fallback Roadmap
    return {
        "title": f"{role.title()} Learning & Career Roadmap",
        "description": f"Master key skills, frameworks, and system design concepts required for a {role} position.",
        "estimated_duration": "4 - 6 Months",
        "phases": [
            {
                "phase_number": 1,
                "title": "Foundations & Core Principles",
                "duration": "4 Weeks",
                "summary": "Build strong underlying principles, syntax, tools, and basic concepts.",
                "topics": ["Core Language & Framework Fundamentals", "Essential Tooling & Environment Setup", "Basic Architecture & File Structure", "Version Control (Git & GitHub)", "Code Formatting & Standards"],
                "recommended_project": "Build an introductory hands-on project demonstrating foundational concepts",
                "interview_focus": "Syntax, basic data structures, core definitions, and foundational concepts."
            },
            {
                "phase_number": 2,
                "title": "Intermediate Application & Patterns",
                "duration": "5 Weeks",
                "summary": "Develop real-world application components, integrations, and architectural patterns.",
                "topics": ["API Integration & Asynchronous Workflows", "Data Management & Storage", "State & Control Management", "Error Handling & Debugging Techniques", "Security & Validation Principles"],
                "recommended_project": "Develop a multi-featured application with data storage and external API integration",
                "interview_focus": "State flow, error handling strategies, asynchronous operations, and performance tuning."
            },
            {
                "phase_number": 3,
                "title": "Advanced Engineering & Testing",
                "duration": "4 Weeks",
                "summary": "Master automated testing, performance optimization, and architectural best practices.",
                "topics": ["Automated Unit & Integration Testing", "Performance Profiling & Bottleneck Resolution", "Security Hardening & Best Practices", "Scalability & Modular Refactoring", "CI/CD Pipeline Setup"],
                "recommended_project": "Add robust test suites, CI/CD automation, and optimization to your project",
                "interview_focus": "Testing strategies, refactoring patterns, micro vs macro architecture trade-offs."
            },
            {
                "phase_number": 4,
                "title": "System Design & Interview Readiness",
                "duration": "3 Weeks",
                "summary": "Prepare for high-level technical interviews, system design rounds, and portfolio presentations.",
                "topics": ["High-Level System Design & Scaling", "Portfolio & Project Documentation", "Mock Technical Interview Practice", "Behavioral Interview Prep (STAR method)", "Resume & LinkedIn Optimization"],
                "recommended_project": "Deploy your complete portfolio project with architecture diagram and live demo link",
                "interview_focus": "System design trade-offs, STAR situational answers, and portfolio walkthrough."
            }
        ]
    }


def generate_resume_jd_questions_groq(resume_text: str, job_description: str, n: int = 5, difficulty: int = 3) -> list:
    """
    Generate tailored interview questions based on candidate's resume and job description.
    """
    r_snippet = (resume_text or "General background in software and technology.")[:4000]
    jd_snippet = (job_description or "General software engineering role.")[:4000]
    
    prompt = f"""
You are an expert executive interviewer and senior hiring manager conducting a tailored technical interview.

CANDIDATE RESUME HIGHLIGHTS:
{r_snippet}

TARGET JOB DESCRIPTION:
{jd_snippet}

TASK:
Generate exactly {n} highly targeted interview questions specifically tailored to this candidate and job posting.

RULES:
- Questions MUST directly evaluate the candidate's actual projects, skills, tools, or achievements mentioned in their resume against the specific requirements, tech stack, and responsibilities of the job description.
- Include a mix of technical depth, experience validation, project architecture, and role-fit situational scenarios.
- Do NOT output extra text or markdown wrappers. Output ONLY a valid JSON array of objects.

JSON FORMAT:
[
  {{
    "text": "Based on your resume experience with [Tool/Project], how would you design [Requirement from Job Description]?",
    "keywords": "skill1, skill2, concept",
    "difficulty": {difficulty}
  }}
]
"""
    try:
        response = _call_groq_chat(prompt, temperature=0.25)
        start = response.find("[")
        end = response.rfind("]")
        if start != -1 and end > start:
            parsed = json.loads(response[start:end+1])
            if isinstance(parsed, list) and len(parsed) > 0:
                return parsed[:n]
    except Exception as e:
        logging.getLogger(__name__).exception("Failed to generate Resume/JD questions: %s", e)

    return [
        {
            "text": "Walk me through a key project on your resume and how your technical decisions align with the core requirements of this job description.",
            "keywords": "resume, experience, project, skills",
            "difficulty": difficulty
        },
        {
            "text": "What is the most technically challenging problem you solved in your past experience, and how does that prepare you for the responsibilities in this job posting?",
            "keywords": "problem solving, architecture, impact",
            "difficulty": difficulty
        },
        {
            "text": "Comparing your resume background to the target job description requirements, which core framework or technology is your strongest suit?",
            "keywords": "strengths, skills match, technical fit",
            "difficulty": difficulty
        }
    ]


