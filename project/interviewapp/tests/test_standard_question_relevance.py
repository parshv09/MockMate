"""
Regression tests for Normal Interview Question Relevance (Direct Structured LLM Path).

Verifies:
1. Normal Interview bypasses shared static RAG even when RAG_ENABLED=True.
2. Direct generation receives exact role, job_role, difficulty, and n_questions.
3. Backend Developer prompt avoids unrelated frontend requirements and constrains domain.
4. Numeric technical questions (HTTP 404/500, O(1), 3NF, Python 3) are preserved.
5. Genuine mathematical questions are still classified as "math".
6. Role-aware fallback receives and uses job_role.
7. Deduplication removes exact and near-duplicate questions.
8. Difficulty constraints are represented in the generated prompt.
9. Resume/JD generation continues to use its existing RAG pipeline unchanged.
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from interviewapp.models import Resume
from interviewapp.qgen_groq import (
    _build_prompt,
    _is_math_question_textual,
    generate_questions_groq,
)
from interviewapp.services.session_service import (
    create_resume_jd_session,
    create_standard_session,
)
from interviewapp.views_helpers import generate_question_stub

User = get_user_model()


class StandardQuestionRelevanceTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="relevance_user",
            password="Password123!",
        )

    @override_settings(RAG_ENABLED=True)
    def test_normal_interview_bypasses_shared_rag_even_when_rag_enabled(self):
        sample_questions = [
            {
                "text": "How do you optimize slow PostgreSQL queries using EXPLAIN ANALYZE?",
                "keywords": "postgresql,explain,index,query",
                "difficulty": 3,
                "type": "reasoning",
            },
            {
                "text": "Explain how Django REST Framework handles serializer validation and permissions.",
                "keywords": "drf,serializer,permissions",
                "difficulty": 3,
                "type": "reasoning",
            },
        ]

        with patch(
            "interviewapp.services.session_service.generate_questions_with_rag",
            side_effect=AssertionError("Shared static RAG must NOT be called for Normal Interview"),
        ), patch(
            "interviewapp.services.session_service.generate_questions_groq",
            return_value=sample_questions,
        ) as groq_mock:
            session, created_count = create_standard_session(
                user=self.user,
                raw_role="tech",
                job_role="Backend Developer",
                difficulty=3,
                n_questions=2,
            )

        groq_mock.assert_called_once_with(
            role="Technical",
            job_role="Backend Developer",
            n=2,
            difficulty=3,
            previous_questions=[],
        )
        self.assertEqual(created_count, 2)
        self.assertEqual(session.role, "tech")
        self.assertEqual(session.job_role, "Backend Developer")
        self.assertEqual(session.difficulty, 3)
        self.assertEqual(session.answers.count(), 2)
        self.assertEqual(session.answers.first().question.source, "llm")

    def test_backend_developer_prompt_constrains_role_focus_and_difficulty(self):
        prompt_mid = _build_prompt(
            role="Technical",
            job_role="Backend Developer",
            n=5,
            difficulty=3,
            math_needed=0,
        )
        self.assertIn("Backend Developer", prompt_mid)
        self.assertIn("Technical", prompt_mid)
        self.assertIn("3/5", prompt_mid)
        self.assertIn("do NOT introduce unrelated frontend/UI questions for backend roles", prompt_mid)

        prompt_entry = _build_prompt(
            role="Technical",
            job_role="Backend Developer",
            n=3,
            difficulty=1,
            math_needed=0,
        )
        self.assertIn("ENTRY-LEVEL", prompt_entry)
        self.assertIn("Do NOT ask about distributed systems", prompt_entry)

        prompt_senior = _build_prompt(
            role="Technical",
            job_role="Backend Developer",
            n=3,
            difficulty=5,
            math_needed=0,
        )
        self.assertIn("SENIOR / EXPERT", prompt_senior)
        self.assertIn("5/5", prompt_senior)

    def test_numeric_technical_questions_are_not_misclassified_as_math(self):
        tech_questions = [
            "Explain the difference between HTTP 404 and 500 status codes.",
            "Compare O(1) and O(n) time complexity with hash map examples.",
            "Explain database normalization up to 3NF and when to denormalize.",
            "What changed in Python 3 regarding string encoding and division?",
        ]
        for q_text in tech_questions:
            self.assertFalse(
                _is_math_question_textual(q_text),
                f"Technical question was wrongly classified as math: {q_text}",
            )

        payload = json.dumps([
            {"text": q, "keywords": "backend,api,sql", "difficulty": 3, "type": "reasoning"}
            for q in tech_questions
        ])
        with patch("interviewapp.qgen_groq._call_groq_chat", return_value=payload) as call_mock:
            result = generate_questions_groq(
                role="Technical",
                job_role="Backend Developer",
                n=4,
                difficulty=3,
            )
        # Should succeed in a single LLM call without stripping any of the 4 technical questions
        self.assertEqual(call_mock.call_count, 1)
        self.assertEqual(len(result), 4)
        self.assertEqual([q["text"] for q in result], tech_questions)

    def test_genuine_mathematical_questions_still_classified_as_math(self):
        math_questions = [
            "Calculate the probability of drawing two aces in a row without replacement.",
            "If 10 servers cost $250 per month, how much do 4 servers cost?",
            "What is the next number in the series 2, 6, 18, 54?",
            "Compute 15% of 240 and explain your steps.",
        ]
        for q_text in math_questions:
            self.assertTrue(
                _is_math_question_textual(q_text),
                f"Genuine math question was not classified as math: {q_text}",
            )

    def test_role_aware_fallback_stub_uses_job_role_and_difficulty(self):
        stub_backend = generate_question_stub("tech", difficulty=3, job_role="Backend Developer")
        self.assertIn("Backend Developer", stub_backend["text"])
        self.assertEqual(stub_backend["difficulty"], 3)

        # Backward compatibility when job_role is omitted
        stub_default = generate_question_stub("hr", difficulty=2)
        self.assertTrue(bool(stub_default["text"]))
        self.assertEqual(stub_default["difficulty"], 2)

    def test_deduplication_filters_exact_and_near_duplicate_questions(self):
        previous = ["Explain how database indexing improves SELECT query performance in PostgreSQL."]
        llm_payload = json.dumps([
            # Near-duplicate of previous question (>80% similar)
            {
                "text": "Explain how database indexing improves SELECT query performance in Postgres.",
                "keywords": "index,sql",
                "difficulty": 3,
                "type": "reasoning",
            },
            # Valid unique question #1
            {
                "text": "How do you design idempotent REST API endpoints for payment retries?",
                "keywords": "idempotency,rest,api",
                "difficulty": 3,
                "type": "reasoning",
            },
            # Near-duplicate of valid question #1 within same batch
            {
                "text": "How do you design idempotent REST API endpoints for payment retry requests?",
                "keywords": "idempotency,rest,api",
                "difficulty": 3,
                "type": "reasoning",
            },
            # Valid unique question #2
            {
                "text": "How do Django database transactions and select_for_update prevent race conditions?",
                "keywords": "django,transactions,locking",
                "difficulty": 3,
                "type": "reasoning",
            },
        ])

        with patch("interviewapp.qgen_groq._call_groq_chat", return_value=llm_payload):
            result = generate_questions_groq(
                role="Technical",
                job_role="Backend Developer",
                n=2,
                difficulty=3,
                previous_questions=previous,
            )

        self.assertEqual(len(result), 2)
        texts = [q["text"] for q in result]
        self.assertIn("How do you design idempotent REST API endpoints for payment retries?", texts)
        self.assertIn("How do Django database transactions and select_for_update prevent race conditions?", texts)

    @override_settings(RAG_ENABLED=True)
    def test_resume_jd_session_still_uses_resume_rag_pipeline(self):
        resume = Resume.objects.create(
            user=self.user,
            title="Backend Resume",
            extracted_text="Built Django REST APIs and PostgreSQL microservices.",
        )
        rag_questions = [
            {
                "text": "Walk me through the Django REST APIs on your Backend Resume.",
                "keywords": "django,rest,api",
                "difficulty": 3,
                "type": "reasoning",
            }
        ]
        with patch(
            "interviewapp.services.session_service.generate_resume_jd_rag_questions",
            return_value=rag_questions,
        ) as resume_rag_mock, patch(
            "interviewapp.services.session_service.generate_questions_groq",
            side_effect=AssertionError("Resume/JD session should use resume RAG when RAG_ENABLED=True"),
        ):
            session, count = create_resume_jd_session(
                user=self.user,
                resume_obj=resume,
                job_description="Senior Backend Developer with Django and PostgreSQL",
                difficulty=3,
                n_questions=1,
            )

        resume_rag_mock.assert_called_once()
        self.assertEqual(count, 1)
        self.assertEqual(session.answers.first().question.source, "rag_resume")

    def test_hr_prompt_generates_standard_hr_questions_without_role_or_tech_difficulty_lock(self):
        prompt_hr = _build_prompt(
            role="Human Resources",
            job_role="Backend Developer",
            n=5,
            difficulty=5,
            math_needed=0,
        )
        self.assertIn("standard HR interview questions", prompt_hr)
        self.assertIn("Do NOT tie every question to the candidate's specific job role", prompt_hr)
        self.assertIn("1 direct sentence", prompt_hr)
        self.assertNotIn("SENIOR / EXPERT", prompt_hr)
        self.assertNotIn("long sections of code", prompt_hr)
        self.assertIn("do NOT apply technical difficulty levels", prompt_hr)

