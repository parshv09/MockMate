# interviewapp/views_helpers.py
import random

def generate_question_stub(role, difficulty=2):
    """
    A simple fallback question generator used only when Groq API fails.
    Generates varied, unique-ish questions using templates.
    """

    tech_terms = [
        "process",
        "thread",
        "database indexing",
        "REST API",
        "authentication",
        "caching",
        "load balancing",
        "microservices",
        "HTTP protocol",
        "Docker container"
    ]

    scenarios = [
        "a production outage",
        "a conflicting requirement",
        "a tight deadline",
        "scaling the system to 10x",
        "optimizing slow database queries",
        "managing teamwork conflicts",
        "debugging a critical bug",
        "handling unexpected edge cases"
    ]

    templates = {
        'tech': [
            "Explain how {a} works and give an example.",
            "Describe the difference between {a} and {b} with a real-life example.",
            "How would you troubleshoot issues related to {a}?",
            "Design a small system using {a} and explain the flow.",
            "What are common mistakes developers make with {a}?"
        ],
        'hr': [
            "Tell me about a time you handled {scenario}.",
            "Describe your strengths and weaknesses in a real situation.",
            "How do you deal with conflicts inside a team?",
            "Why do you think you are a good fit for this role?",
            "Describe your biggest achievement and how you reached it."
        ],
        'apt': [
            "If {n} people share {m} items, how many items per person? Explain reasoning.",
            "Solve a real-life problem using ratios or percentages.",
            "Explain how to break a complex problem into smaller steps.",
            "Given a series: 2, 6, 18… find the next term and justify.",
            "How do you approach solving optimization problems?"
        ],
        'beh': [
            "Tell me about a time you had to make a quick decision under pressure.",
            "Describe a failure you experienced and what you learned.",
            "How do you motivate yourself during repetitive tasks?",
            "Explain a situation where you took leadership voluntarily.",
            "Describe how you handle criticism or negative feedback."
        ]
    }

    # choose a category (fallback if role missing)
    role_key = role if role in templates else 'tech'

    # choose template
    template = random.choice(templates[role_key])

    # fill random variables
    a = random.choice(tech_terms)
    b = random.choice([t for t in tech_terms if t != a])
    scenario = random.choice(scenarios)
    n = random.randint(2, 20)
    m = random.randint(5, 100)

    # fill template values
    text = template.format(a=a, b=b, scenario=scenario, n=n, m=m).strip()

    # generate keywords
    keywords = []
    for kw in [a, b, scenario.split()[0], "explain"]:
        if kw and len(keywords) < 4:
            keywords.append(kw.lower())

    return {
        "text": text,
        "keywords": ",".join(keywords),
        "difficulty": difficulty,
    }
