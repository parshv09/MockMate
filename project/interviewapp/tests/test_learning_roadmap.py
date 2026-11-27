"""
Unit and API integration tests for Dynamic Learning Roadmap (Milestone 1).
"""

import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from interviewapp.models import Answer, GeneratedQuestion, InterviewSession, LearningRoadmap
from interviewapp.qgen_groq import generate_learning_roadmap_groq
from interviewapp.services.roadmap_service import (
    RoadmapGenerationInProgressError,
    analyze_session_skill_gaps,
)

User = get_user_model()


class LearningRoadmapSkillGapTests(APITestCase):
    """Tests for deterministic skill-gap analysis and priority ranking (zero Groq calls)."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="gap_user",
            email="gap@example.com",
            password="Password123!",
        )

    def _new_session(self, *, completed=True, role="tech", job_role="Backend Engineer"):
        return InterviewSession.objects.create(
            user=self.user,
            role=role,
            job_role=job_role,
            difficulty=3,
            state="adaptive",
            completed=completed,
            total_questions=1,
        )

    def test_high_medium_low_priorities_skips_followups_and_resume_grounding(self):
        session = self._new_session()
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain PostgreSQL indexing.", keywords="postgres", signature="lg-q1"
        )
        q2 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain Redis TTL.", keywords="redis", signature="lg-q2"
        )
        q2_fu = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Follow-up on Redis eviction.", keywords="redis", signature="lg-q2fu"
        )
        q3 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain REST pagination.", keywords="rest", signature="lg-q3"
        )
        q4 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain Docker multi-stage builds.", keywords="docker", signature="lg-q4"
        )

        # Q1: Skipped -> High
        Answer.objects.create(
            session=session, question=q1, index=1, answer_text="[Skipped]", score=0, processed=True
        )
        # Q2 + Follow-up: 55 and 65 -> cluster avg 60 -> Medium (single cluster, not 2 independent)
        a2 = Answer.objects.create(
            session=session, question=q2, index=2, answer_text="TTL expires keys.", score=55, processed=True
        )
        Answer.objects.create(
            session=session, question=q2_fu, parent_answer=a2, index=3, answer_text="LRU evicts.", score=65, processed=True
        )
        # Q3: Strong score (85) with missed resume point -> Low
        Answer.objects.create(
            session=session,
            question=q3,
            index=4,
            answer_text="Cursor pagination scales well.",
            score=85,
            processed=True,
            resume_grounding={"missed_resume_points": ["Mentioned cursor pagination on 10M rows"]},
        )
        # Q4: High score (82) with resume contradiction -> High
        Answer.objects.create(
            session=session,
            question=q4,
            index=5,
            answer_text="Used single stage only.",
            score=82,
            processed=True,
            resume_grounding={"contradictions": ["Resume claims multi-stage Docker optimization"]},
        )

        result = analyze_session_skill_gaps(session)
        self.assertTrue(result["has_sufficient_evidence"])
        self.assertEqual(result["evaluated_interactions"], 4)  # 4 main clusters (follow-up grouped)

        by_concept = {g["concept"]: g for g in result["skill_gaps"]}
        self.assertEqual(by_concept["PostgreSQL"]["priority"], "High")
        self.assertEqual(by_concept["Docker"]["priority"], "High")
        self.assertEqual(by_concept["Redis Caching"]["priority"], "Medium")
        self.assertEqual(by_concept["Redis Caching"]["attempt_count"], 1)
        self.assertEqual(by_concept["REST APIs"]["priority"], "Low")

    def test_repeated_weak_concepts_promote_to_high_priority(self):
        session = self._new_session()
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Caching Q1", keywords="caching", signature="rep-1"
        )
        q2 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Caching Q2", keywords="cache", signature="rep-2"
        )
        Answer.objects.create(
            session=session, question=q1, index=1, answer_text="A1", score=58, processed=True
        )
        Answer.objects.create(
            session=session, question=q2, index=2, answer_text="A2", score=60, processed=True
        )

        result = analyze_session_skill_gaps(session)
        self.assertEqual(len(result["skill_gaps"]), 1)
        gap = result["skill_gaps"][0]
        self.assertEqual(gap["concept"], "Caching")
        self.assertEqual(gap["attempt_count"], 2)
        self.assertEqual(gap["priority"], "High")

    def test_strong_performance_with_no_signals_invents_no_gaps(self):
        session = self._new_session()
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain HTTP.", keywords="http", signature="strong-1"
        )
        Answer.objects.create(
            session=session, question=q1, index=1, answer_text="Complete answer.", score=92, processed=True
        )
        result = analyze_session_skill_gaps(session)
        self.assertTrue(result["has_sufficient_evidence"])
        self.assertEqual(result["evidence_status"], "strong_no_gaps")
        self.assertEqual(result["skill_gaps"], [])

    def test_insufficient_evidence_returns_empty_gaps(self):
        session = self._new_session()
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Unanswered Q1", keywords="sql", signature="insuff-1"
        )
        Answer.objects.create(session=session, question=q1, index=1, processed=False)

        result = analyze_session_skill_gaps(session)
        self.assertFalse(result["has_sufficient_evidence"])
        self.assertEqual(result["evidence_status"], "insufficient_evidence")
        self.assertEqual(result["skill_gaps"], [])


class LearningRoadmapGenerationTests(APITestCase):
    """Tests for Groq roadmap generation, schema normalization, and deterministic fallbacks."""

    SAMPLE_GAPS = {
        "has_sufficient_evidence": True,
        "evidence_status": "sufficient",
        "evaluated_interactions": 1,
        "skill_gaps": [
            {
                "concept": "Database Indexing",
                "subject": "TECH",
                "priority": "High",
                "avg_score": 35.0,
                "attempt_count": 1,
                "skip_count": 0,
                "followup_count": 0,
                "scope": "isolated_question",
                "demonstrated_weaknesses": ["Average score of 35% across 1 interaction(s)."],
                "improvement_opportunities": ["Explain B-tree trade-offs"],
            }
        ],
    }

    @patch("interviewapp.qgen_groq._call_groq_chat")
    def test_valid_groq_response_normalized_and_urls_sanitized(self, mock_groq):
        mock_groq.return_value = json.dumps(
            {
                "title": "Backend Study Plan",
                "overview": "Focus on database indexing.",
                "estimated_hours": 6,
                "learning_steps": [
                    {
                        "order": 1,
                        "concept": "Database Indexing",
                        "subject": "Databases",
                        "priority": "high",
                        "why_needed": "Low score on indexing.",
                        "learning_objectives": ["Understand B-tree lookups"],
                        "how_to_learn": "Read docs and run EXPLAIN.",
                        "practical_example": "CREATE INDEX idx_users_email ON users(email);",
                        "exercise": "Benchmark query before and after index.",
                        "interview_questions": ["When does an index slow down writes?"],
                        "resources": [
                            "PostgreSQL Docs https://example.com/fake-url",
                            "Use The Index, Luke",
                        ],
                        "expected_outcome": "Explain index trade-offs clearly.",
                    }
                ],
            }
        )

        roadmap = generate_learning_roadmap_groq(self.SAMPLE_GAPS, role="tech", job_role="Backend Engineer")
        self.assertEqual(roadmap["title"], "Backend Study Plan")
        self.assertEqual(len(roadmap["learning_steps"]), 1)
        step = roadmap["learning_steps"][0]
        self.assertEqual(step["priority"], "High")
        # Fabricated URL must be stripped
        for res_item in step["resources"]:
            self.assertNotIn("http://", res_item)
            self.assertNotIn("https://", res_item)

    @patch("interviewapp.qgen_groq._call_groq_chat", return_value="not valid json at all")
    def test_invalid_json_falls_back_deterministically_using_actual_gaps(self, _mock_groq):
        roadmap = generate_learning_roadmap_groq(self.SAMPLE_GAPS, role="tech", job_role="Backend Engineer")
        self.assertEqual(len(roadmap["learning_steps"]), 1)
        self.assertEqual(roadmap["learning_steps"][0]["concept"], "Database Indexing")
        self.assertEqual(roadmap["learning_steps"][0]["priority"], "High")

    @patch("interviewapp.qgen_groq._call_groq_chat", side_effect=RuntimeError("Groq timeout"))
    def test_groq_failure_falls_back_deterministically(self, _mock_groq):
        roadmap = generate_learning_roadmap_groq(self.SAMPLE_GAPS, role="tech", job_role="Backend Engineer")
        self.assertEqual(len(roadmap["learning_steps"]), 1)
        self.assertEqual(roadmap["learning_steps"][0]["concept"], "Database Indexing")


class LearningRoadmapAPITests(APITestCase):
    """API tests for GET/POST /api/v1/sessions/<pk>/learning-roadmap/."""

    def setUp(self):
        cache.clear()
        self.user_a = User.objects.create_user(
            username="rm_user_a", email="rma@example.com", password="PasswordA123!"
        )
        self.user_b = User.objects.create_user(
            username="rm_user_b", email="rmb@example.com", password="PasswordB123!"
        )
        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)

        self.session = InterviewSession.objects.create(
            user=self.user_a,
            role="tech",
            job_role="Python Backend Engineer",
            difficulty=3,
            state="adaptive",
            completed=True,
            total_questions=1,
        )
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain Django ORM.", keywords="django orm", signature="rm-api-q1"
        )
        Answer.objects.create(
            session=self.session,
            question=q1,
            index=1,
            answer_text="ORM maps tables.",
            score=45,
            feedback="Mention select_related.",
            improvement_tips=["Explain N+1 query optimization"],
            processed=True,
        )
        self.url = reverse("api_v1:session_learning_roadmap", kwargs={"pk": self.session.id})

    def test_ownership_and_incomplete_session_guards(self):
        # Unauthenticated
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_401_UNAUTHORIZED)

        # User B -> 404
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(self.client.post(self.url, {}, format="json").status_code, status.HTTP_404_NOT_FOUND)

        # Incomplete session -> 400
        incomplete = InterviewSession.objects.create(
            user=self.user_a, role="tech", job_role="Dev", completed=False, total_questions=1
        )
        inc_url = reverse("api_v1:session_learning_roadmap", kwargs={"pk": incomplete.id})
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        self.assertEqual(self.client.get(inc_url).status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.client.post(inc_url, {}, format="json").status_code, status.HTTP_400_BAD_REQUEST)

    @patch("interviewapp.qgen_groq._call_groq_chat")
    def test_generate_cached_retrieval_and_explicit_regeneration(self, mock_groq):
        mock_groq.return_value = json.dumps(
            {
                "title": "Python Roadmap v1",
                "overview": "Focus on Django ORM.",
                "estimated_hours": 4,
                "learning_steps": [
                    {
                        "order": 1,
                        "concept": "Django ORM",
                        "subject": "TECH",
                        "priority": "High",
                        "why_needed": "Score 45%",
                        "learning_objectives": ["Prevent N+1 queries"],
                        "how_to_learn": "Study select_related and prefetch_related.",
                        "practical_example": "Book.objects.select_related('author')",
                        "exercise": "Optimize a view with 20 queries down to 2.",
                        "interview_questions": ["Difference between select_related and prefetch_related?"],
                        "resources": ["Django QuerySet API documentation"],
                        "expected_outcome": "Optimize ORM queries.",
                    }
                ],
            }
        )

        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

        # GET before generation -> 404
        self.assertEqual(self.client.get(self.url).status_code, status.HTTP_404_NOT_FOUND)

        # POST generates and persists -> 201
        res_create = self.client.post(self.url, {}, format="json")
        self.assertEqual(res_create.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res_create.data["roadmap_json"]["title"], "Python Roadmap v1")
        self.assertEqual(mock_groq.call_count, 1)

        # GET returns cached -> 200 without calling Groq
        res_get = self.client.get(self.url)
        self.assertEqual(res_get.status_code, status.HTTP_200_OK)
        self.assertEqual(res_get.data["roadmap_json"]["title"], "Python Roadmap v1")
        self.assertEqual(mock_groq.call_count, 1)

        # POST with regenerate=false returns cached -> 200 without calling Groq
        res_cached = self.client.post(self.url, {"regenerate": False}, format="json")
        self.assertEqual(res_cached.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_groq.call_count, 1)

        # Explicit regenerate=true -> calls Groq again and updates persisted roadmap
        mock_groq.return_value = json.dumps(
            {
                "title": "Python Roadmap v2",
                "overview": "Updated roadmap.",
                "estimated_hours": 5,
                "learning_steps": [
                    {
                        "order": 1,
                        "concept": "Django ORM",
                        "subject": "TECH",
                        "priority": "High",
                        "why_needed": "Score 45%",
                        "learning_objectives": ["Query optimization"],
                        "how_to_learn": "Profile SQL.",
                        "practical_example": "Prefetch('tags')",
                        "exercise": "Use django-debug-toolbar.",
                        "interview_questions": ["How does prefetch_related work?"],
                        "resources": ["Django ORM performance guide"],
                        "expected_outcome": "Write optimal ORM queries.",
                    }
                ],
            }
        )
        res_regen = self.client.post(self.url, {"regenerate": True}, format="json")
        self.assertEqual(res_regen.status_code, status.HTTP_200_OK)
        self.assertEqual(res_regen.data["roadmap_json"]["title"], "Python Roadmap v2")
        self.assertEqual(mock_groq.call_count, 2)
        self.assertEqual(LearningRoadmap.objects.filter(session=self.session).count(), 1)

    @patch("interviewapp.qgen_groq.generate_learning_roadmap_groq", side_effect=RuntimeError("Unexpected crash"))
    def test_regeneration_failure_preserves_previous_roadmap(self, _mock_gen):
        LearningRoadmap.objects.create(
            session=self.session,
            skill_gaps_json=[{"concept": "Django ORM", "priority": "High"}],
            roadmap_json={"title": "Existing Valid Roadmap", "learning_steps": []},
        )
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        res = self.client.post(self.url, {"regenerate": True}, format="json")
        self.assertEqual(res.status_code, status.HTTP_500_INTERNAL_SERVER_ERROR)

        existing = LearningRoadmap.objects.get(session=self.session)
        self.assertEqual(existing.roadmap_json["title"], "Existing Valid Roadmap")

    @patch(
        "interviewapp.api.views.roadmap_views.generate_learning_roadmap_for_session",
        side_effect=RoadmapGenerationInProgressError("Generation in progress"),
    )
    def test_concurrent_duplicate_request_returns_409(self, _mock_in_progress):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        res = self.client.post(self.url, {}, format="json")
        self.assertEqual(res.status_code, status.HTTP_409_CONFLICT)

