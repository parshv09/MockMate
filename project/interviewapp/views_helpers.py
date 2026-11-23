# interviewapp/views_helpers.py
import random

def _select_tech_terms(job_role: str, difficulty: int) -> list:
    jr = (job_role or "").lower()
    if any(k in jr for k in ("backend", "django", "flask", "fastapi", "node", "express", "spring", "api", "server", "python", "java", "go", "golang", "sql", "database")):
        base = [
            "REST API design",
            "database indexing",
            "SQL query optimization",
            "authentication and authorization",
            "caching",
            "error handling and logging",
            "database transactions",
            "input validation",
        ]
        if difficulty >= 4:
            base.extend(["connection pooling", "rate limiting", "horizontal scaling"])
        return base

    if any(k in jr for k in ("frontend", "react", "vue", "angular", "ui", "css", "javascript", "typescript")):
        base = [
            "component state management",
            "DOM event handling",
            "client-side routing",
            "API error handling",
            "accessibility (a11y)",
            "browser rendering performance",
        ]
        if difficulty >= 4:
            base.extend(["code splitting", "memoization", "hydration"])
        return base

    base = [
        "data structures",
        "REST API",
        "authentication",
        "database indexing",
        "error handling",
        "automated testing",
        "caching",
        "version control workflows",
    ]
    if difficulty >= 4:
        base.extend(["load balancing", "microservices", "observability"])
    return base


def _normalize_stub_role(role: str) -> str:
    r = (role or "").strip().lower()
    if r in ("tech", "technical"):
        return "tech"
    if r in ("hr", "human resources"):
        return "hr"
    if r in ("apt", "aptitude"):
        return "apt"
    if r in ("beh", "behavioral"):
        return "beh"
    return "tech"


def generate_question_stub(role, difficulty=2, job_role=""):
    """
    A simple fallback question generator used only when Groq API fails.
    Generates varied, role-calibrated questions using templates.
    """
    diff_val = max(1, min(5, int(difficulty or 2)))
    role_key = _normalize_stub_role(role)
    clean_job_role = (job_role or "").strip() or "Software Engineer"

    tech_terms = _select_tech_terms(clean_job_role, diff_val)

    scenarios = [
        "a conflicting requirement",
        "a tight deadline",
        "debugging a critical issue",
        "managing teamwork conflicts",
        "handling unexpected edge cases",
    ]
    if diff_val >= 3:
        scenarios.extend(["a production outage", "optimizing slow database queries"])

    tech_templates = (
        [
            "As a {job_role}, explain how {a} works and give a practical example.",
            "For a {job_role} role, describe the difference between {a} and {b} with a concrete use case.",
            "What are common mistakes a {job_role} should avoid when working with {a}?",
        ]
        if diff_val <= 2
        else [
            "As a {job_role}, how would you troubleshoot a production issue involving {a}?",
            "For a {job_role} system, describe the trade-offs between {a} and {b} with a real-world example.",
            "How would you design a reliable {job_role} component using {a}, and what edge cases would you handle?",
            "What are common bottlenecks or mistakes a {job_role} encounters with {a}?",
        ]
    )

    templates = {
        'tech': tech_templates,
        'hr': [
            "Tell me about a time you handled {scenario} and what you learned from it.",
            "What are your biggest strengths and one area you are actively working to improve?",
            "How do you handle disagreements or conflicts inside a team?",
            "Where do you see your career heading over the next 2 to 3 years, and what motivates you?",
            "Describe an achievement you are especially proud of and how you worked toward it.",
        ],
        'apt': [
            "If {n} people share {m} items equally and each requires 2 units of setup, how do you distribute them? Explain reasoning.",
            "Solve a resource-allocation problem for a {job_role} team using ratios or percentages.",
            "Explain how to break a complex {job_role} estimation problem into smaller measurable steps.",
            "Given a series: 2, 6, 18… find the next term and justify your rule.",
            "How do you approach solving constraint-optimization problems systematically?",
        ],
        'beh': [
            "Tell me about a time as a {job_role} when you had to make a quick decision under pressure.",
            "Describe a technical or project failure you experienced as a {job_role} and what you learned.",
            "How do you stay organized and maintain quality during repetitive {job_role} tasks?",
            "Explain a situation where you took ownership of a problem outside your immediate scope.",
            "Describe how you handle constructive criticism or negative feedback on your work.",
        ],
    }

    template = random.choice(templates[role_key])

    a = random.choice(tech_terms)
    b = random.choice([t for t in tech_terms if t != a])
    scenario = random.choice(scenarios)
    n = random.randint(2, 20)
    m = random.randint(5, 100)

    text = template.format(
        a=a,
        b=b,
        scenario=scenario,
        n=n,
        m=m,
        job_role=clean_job_role,
    ).strip()

    keywords = []
    for kw in [clean_job_role.lower(), a, b, scenario.split()[0]]:
        if kw and kw not in keywords and len(keywords) < 4:
            keywords.append(kw.lower())

    return {
        "text": text,
        "keywords": ",".join(keywords),
        "difficulty": diff_val,
    }
