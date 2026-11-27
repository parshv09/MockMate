"""
Backend integration & regression tests for Resume/JD Adaptive Interview (Milestone A).
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from interviewapp.models import Answer, GeneratedQuestion, InterviewSession, Resume, SessionQuestion

User = get_user_model()


class ResumeJDAdaptiveAPITests(APITestCase):
    """Tests for Resume/JD sessions upgraded to adaptive progression."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="rjd_adaptive_user",
            email="rjd_adaptive@example.com",
            password="Password123!",
        )
        self.token = str(RefreshToken.for_user(self.user).access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token}")
        self.resume_jd_url = reverse("api_v1:session_resume_jd_create")
        self.resume = Resume.objects.create(
            user=self.user,
            title="Backend Python CV",
            extracted_text="Built Django REST APIs, PostgreSQL indexing, and Redis caching.",
        )

    @patch("interviewapp.services.session_service.generate_resume_jd_rag_questions")
    def test_create_resume_jd_with_existing_resume_creates_adaptive_single_question(self, mock_rag):
        mock_rag.return_value = [
            {
                "text": "Explain how you optimized PostgreSQL queries in your Django project.",
                "keywords": "postgresql,index,django",
                "difficulty": 3,
                "type": "reasoning",
            }
        ]
        res = self.client.post(
            self.resume_jd_url,
            {
                "resume_id": self.resume.id,
                "job_description": "Senior Django Backend Engineer",
                "difficulty": 3,
                "n_questions": 4,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["created_questions"], 1)
        self.assertEqual(res.data["next_question_kind"], "main")
        self.assertEqual(res.data["main_questions_count"], 1)
        self.assertEqual(res.data["max_main_questions"], 4)
        self.assertEqual(res.data["total_interactions"], 1)
        self.assertEqual(res.data["session"]["state"], "adaptive")
        self.assertEqual(res.data["session"]["max_main_questions"], 4)

        session = InterviewSession.objects.get(id=res.data["session"]["id"])
        self.assertEqual(session.answers.count(), 1)
        self.assertIsNone(session.answers.first().parent_answer)
        self.assertEqual(SessionQuestion.objects.filter(session=session).count(), 1)
        mock_rag.assert_called_once()
        self.assertEqual(mock_rag.call_args.kwargs["n"], 1)

    @patch("interviewapp.services.resume_service.index_resume")
    @patch("interviewapp.services.session_service.generate_resume_jd_rag_questions")
    def test_create_resume_jd_with_new_upload_creates_adaptive_session(self, mock_rag, _mock_index):
        mock_rag.return_value = [
            {"text": "Walk through your Kubernetes deployment.", "keywords": "k8s", "difficulty": 3}
        ]
        uploaded = SimpleUploadedFile("cv.txt", b"Kubernetes and Terraform experience.", content_type="text/plain")
        res = self.client.post(
            self.resume_jd_url,
            {
                "resume_title": "DevOps CV",
                "resume_file": uploaded,
                "job_description": "Cloud DevOps Engineer",
                "difficulty": 3,
                "n_questions": 3,
            },
            format="multipart",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["session"]["state"], "adaptive")
        self.assertEqual(res.data["session"]["max_main_questions"], 3)
        session = InterviewSession.objects.get(id=res.data["session"]["id"])
        self.assertEqual(session.answers.count(), 1)
        created_resume = Resume.objects.get(id=session.resume_id)
        if created_resume.original_file:
            created_resume.original_file.delete(save=False)

    @patch("interviewapp.services.session_service.generate_resume_jd_questions_groq")
    def test_create_jd_only_session_uses_groq_jd_generator_and_adaptive_state(self, mock_jd_groq):
        mock_jd_groq.return_value = [
            {"text": "How do you design idempotent REST endpoints?", "keywords": "rest,idempotency", "difficulty": 4}
        ]
        res = self.client.post(
            self.resume_jd_url,
            {
                "job_description": "Backend API Engineer with REST and PostgreSQL",
                "difficulty": 4,
                "n_questions": 5,
            },
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["session"]["state"], "adaptive")
        self.assertEqual(res.data["session"]["max_main_questions"], 5)
        self.assertEqual(res.data["next_question_kind"], "main")
        mock_jd_groq.assert_called_once()
        self.assertEqual(mock_jd_groq.call_args.kwargs["n"], 1)

    @patch("interviewapp.rag.resume_rag.generate_resume_jd_rag_questions")
    @patch("interviewapp.rag.resume_rag.retrieve_resume_context_for_answer")
    @patch("interviewapp.qgen_groq.generate_follow_up_question_groq")
    @patch("interviewapp.services.session_service.generate_resume_jd_rag_questions")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_rag_grounded_followup_next_main_evaluation_and_summary(
        self,
        mock_analyze,
        mock_init_rag,
        mock_followup,
        mock_retrieve_ans,
        mock_next_rag,
    ):
        mock_init_rag.return_value = [
            {"text": "Main Q1: Describe your Redis caching strategy.", "keywords": "redis,ttl", "difficulty": 3}
        ]
        mock_retrieve_ans.return_value = [
            {"text": "Implemented Redis caching reducing DB load by 40%."}
        ]
        mock_followup.side_effect = [
            {"text": "Follow-up Q1: How did you handle cache invalidation for stale keys?", "keywords": "invalidation", "difficulty": 3, "type": "reasoning"},
            {"text": "Follow-up Q2: How did you benchmark the B-tree index speedup?", "keywords": "explain,analyze", "difficulty": 4, "type": "reasoning"},
        ]
        mock_next_rag.return_value = [
            {"text": "Main Q2: How did you tune PostgreSQL indexes?", "keywords": "postgres,index", "difficulty": 4}
        ]
        mock_analyze.side_effect = [
            {
                "score": 55,
                "feedback": "Partial answer; clarify invalidation.",
                "improvement_tips": ["Explain TTL vs write-through"],
                "resume_grounding": {
                    "correctness_score": 30,
                    "consistency_score": 16,
                    "alignment_level": "high",
                    "supported_claims": ["Used Redis caching"],
                    "contradictions": [],
                    "missed_resume_points": ["40% DB load reduction"],
                },
            },
            {
                "score": 82,
                "feedback": "Strong follow-up.",
                "improvement_tips": [],
                "resume_grounding": {
                    "correctness_score": 38,
                    "consistency_score": 18,
                    "alignment_level": "high",
                    "supported_claims": ["Cache invalidation"],
                    "contradictions": [],
                    "missed_resume_points": [],
                },
            },
            {
                "score": 60,
                "feedback": "Partial index explanation.",
                "improvement_tips": [],
                "resume_grounding": None,
            },
            {
                "score": 85,
                "feedback": "Great EXPLAIN ANALYZE walkthrough.",
                "improvement_tips": [],
                "resume_grounding": None,
            },
        ]

        create_res = self.client.post(
            self.resume_jd_url,
            {
                "resume_id": self.resume.id,
                "job_description": "Senior Django & Redis Engineer",
                "difficulty": 3,
                "n_questions": 2,
            },
            format="json",
        )
        sid = create_res.data["session"]["id"]
        submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": sid})
        next_url = reverse("api_v1:session_next_question", kwargs={"pk": sid})

        # 1. Submit Q1 (score=55) -> RAG-grounded follow-up
        r1 = self.client.post(submit_url, {"answer_text": "We cached hot endpoints in Redis."}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r1.data["next_question_kind"], "follow_up")
        self.assertIsNotNone(r1.data["answer"]["resume_grounding"])
        self.assertEqual(r1.data["answer"]["resume_grounding"]["consistency_score"], 16)
        mock_retrieve_ans.assert_called_once()
        fu_kwargs = mock_followup.call_args_list[0].kwargs
        self.assertEqual(fu_kwargs["difficulty"], 3)
        self.assertEqual(fu_kwargs["job_description"], "Senior Django & Redis Engineer")
        self.assertTrue(len(fu_kwargs["resume_chunks"]) == 1)

        # Refresh recovery check on follow-up
        refresh_res = self.client.get(next_url)
        self.assertEqual(refresh_res.status_code, status.HTTP_200_OK)
        self.assertEqual(refresh_res.data["question_kind"], "follow_up")

        # 2. Submit Follow-up Q1 (score=82) -> RAG next_main at adapted difficulty 4
        r2 = self.client.post(submit_url, {"answer_text": "We used write-through invalidation."}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertEqual(r2.data["next_question_kind"], "main")
        self.assertEqual(r2.data["main_questions_count"], 2)
        mock_next_rag.assert_called_once()
        self.assertEqual(mock_next_rag.call_args.kwargs["difficulty"], 4)
        self.assertIn("Main Q1: Describe your Redis caching strategy.", mock_next_rag.call_args.kwargs["previous_questions"])

        # 3. Submit Final Main Q2 (score=60) -> Final follow-up
        r3 = self.client.post(submit_url, {"answer_text": "Added composite indexes."}, format="json")
        self.assertEqual(r3.status_code, status.HTTP_200_OK)
        self.assertEqual(r3.data["next_question_kind"], "follow_up")

        # 4. Submit Final Follow-up (score=85) -> Completed
        r4 = self.client.post(submit_url, {"answer_text": "Verified with EXPLAIN ANALYZE."}, format="json")
        self.assertEqual(r4.status_code, status.HTTP_200_OK)
        self.assertTrue(r4.data["is_session_completed"])

        # Summary & PDF compatibility
        with patch("interviewapp.services.session_service.generate_session_suggestions", return_value={
            "strengths": ["Strong Redis"], "improvements": [], "overall_tip": "Great", "resources": []
        }), patch("interviewapp.services.session_service.generate_expected_answer", return_value="Model answer"):
            sum_res = self.client.get(reverse("api_v1:session_summary", kwargs={"pk": sid}))
        self.assertEqual(sum_res.status_code, status.HTTP_200_OK)
        self.assertEqual(sum_res.data["session"]["main_questions_count"], 2)
        self.assertEqual(sum_res.data["session"]["total_questions"], 4)
        self.assertIsNotNone(sum_res.data["resume_summary"])

        pdf_res = self.client.get(reverse("api_v1:session_report_download", kwargs={"pk": sid}))
        self.assertEqual(pdf_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_res["Content-Type"], "application/pdf")

    @override_settings(RAG_ENABLED=False)
    @patch("interviewapp.qgen_groq.generate_resume_jd_questions_groq")
    @patch("interviewapp.services.session_service.generate_resume_jd_questions_groq")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_non_rag_fallback_next_main_passes_previous_questions_and_handles_skip(
        self, mock_analyze, mock_init_groq, mock_next_groq
    ):
        mock_init_groq.return_value = [
            {"text": "Fallback Q1", "keywords": "api", "difficulty": 3}
        ]
        mock_next_groq.return_value = [
            {"text": "Fallback Q2", "keywords": "db", "difficulty": 2}
        ]
        create_res = self.client.post(
            self.resume_jd_url,
            {
                "resume_id": self.resume.id,
                "job_description": "Backend Engineer",
                "difficulty": 3,
                "n_questions": 2,
            },
            format="json",
        )
        sid = create_res.data["session"]["id"]
        skip_url = reverse("api_v1:session_adaptive_question_skip", kwargs={"pk": sid})

        s1 = self.client.post(skip_url, {}, format="json")
        self.assertEqual(s1.status_code, status.HTTP_200_OK)
        self.assertEqual(s1.data["next_question_kind"], "main")
        self.assertEqual(s1.data["next_question"]["difficulty"], 2)
        mock_next_groq.assert_called_once()
        self.assertIn("Fallback Q1", mock_next_groq.call_args.kwargs["previous_questions"])
        mock_analyze.assert_not_called()

    @patch("interviewapp.qgen_groq.generate_follow_up_question_groq", side_effect=RuntimeError("Groq timeout"))
    @patch("interviewapp.services.session_service.generate_resume_jd_rag_questions")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_idempotent_retry_and_groq_failure_fallback_in_resume_jd_adaptive(
        self, mock_analyze, mock_init_rag, _mock_fu_err
    ):
        mock_init_rag.return_value = [
            {"text": "Q1: Explain Django ORM.", "keywords": "orm", "difficulty": 3}
        ]
        mock_analyze.return_value = {
            "score": 55,
            "feedback": "Partial answer.",
            "improvement_tips": [],
            "resume_grounding": None,
        }
        create_res = self.client.post(
            self.resume_jd_url,
            {"resume_id": self.resume.id, "job_description": "Django Dev", "difficulty": 3, "n_questions": 2},
            format="json",
        )
        sid = create_res.data["session"]["id"]
        session = InterviewSession.objects.get(id=sid)
        ans1 = session.answers.get(index=1)
        submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": sid})

        # Groq follow-up fails -> falls back safely to stub without losing evaluated answer
        r1 = self.client.post(submit_url, {"answer_id": ans1.id, "answer_text": "ORM maps models."}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(r1.data["next_question_kind"], "follow_up")
        self.assertEqual(session.answers.count(), 2)

        # Retry same answer_id -> returns exact same follow-up without re-evaluating
        r_retry = self.client.post(submit_url, {"answer_id": ans1.id, "answer_text": "ORM maps models."}, format="json")
        self.assertEqual(r_retry.status_code, status.HTTP_200_OK)
        self.assertEqual(r_retry.data["next_question"]["id"], r1.data["next_question"]["id"])
        self.assertEqual(mock_analyze.call_count, 1)
        self.assertEqual(session.answers.count(), 2)

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_legacy_in_progress_resume_jd_session_keeps_fixed_progression(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 55,
            "feedback": "Good.",
            "improvement_tips": [],
            "resume_grounding": None,
        }
        legacy_session = InterviewSession.objects.create(
            user=self.user,
            resume=self.resume,
            job_description="Legacy Backend Role",
            role="tech",
            job_role="Job Match: Legacy Backend Role",
            difficulty=3,
            state="in_progress",
            max_main_questions=0,
            total_questions=2,
            current_index=1,
        )
        q1 = GeneratedQuestion.objects.create(role="tech", difficulty=3, text="Legacy Q1", signature="leg-q1")
        q2 = GeneratedQuestion.objects.create(role="tech", difficulty=3, text="Legacy Q2", signature="leg-q2")
        ans1 = Answer.objects.create(session=legacy_session, question=q1, index=1)
        Answer.objects.create(session=legacy_session, question=q2, index=2)

        legacy_submit_url = reverse("api_v1:session_answer_submit", kwargs={"pk": legacy_session.id})
        res = self.client.post(legacy_submit_url, {"answer_id": ans1.id, "answer_text": "Legacy answer"}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertFalse(res.data["is_session_completed"])
        # Advances directly to pre-allocated Q2 (no adaptive follow-up)
        self.assertEqual(res.data["next_question"]["id"], q2.id)
        self.assertEqual(legacy_session.answers.count(), 2)

