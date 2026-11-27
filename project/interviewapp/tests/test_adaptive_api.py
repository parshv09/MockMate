"""
Integration and regression tests for Hybrid Adaptive Interview Milestone 2 REST APIs:
- POST /api/v1/sessions/adaptive/
- POST /api/v1/sessions/<id>/adaptive/answers/
- POST /api/v1/sessions/<id>/adaptive/skip/
- Idempotency, concurrency, failure recovery, and Session Summary / PDF compatibility.
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken

from interviewapp.models import Answer, GeneratedQuestion, InterviewSession, SessionQuestion
from interviewapp.services.adaptive_service import advance_adaptive_session_from_answer

User = get_user_model()


class AdaptiveSessionAPITests(APITestCase):
    """End-to-end API tests for Hybrid Adaptive Interview lifecycle."""

    def setUp(self):
        self.user_a = User.objects.create_user(
            username="adaptive_api_a",
            email="adaptive_api_a@example.com",
            password="PasswordA123!",
        )
        self.user_b = User.objects.create_user(
            username="adaptive_api_b",
            email="adaptive_api_b@example.com",
            password="PasswordB123!",
        )
        self.token_a = str(RefreshToken.for_user(self.user_a).access_token)
        self.token_b = str(RefreshToken.for_user(self.user_b).access_token)
        self.adaptive_create_url = reverse("api_v1:session_adaptive_create")

    def _auth_a(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_a}")

    def _auth_b(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.token_b}")

    def test_adaptive_create_requires_auth_and_validates_inputs(self):
        res_unauth = self.client.post(self.adaptive_create_url, {"role": "tech"}, format="json")
        self.assertEqual(res_unauth.status_code, status.HTTP_401_UNAUTHORIZED)

        self._auth_a()
        res_bad_role = self.client.post(self.adaptive_create_url, {"role": "unknown"}, format="json")
        self.assertEqual(res_bad_role.status_code, status.HTTP_400_BAD_REQUEST)

        res_bad_diff = self.client.post(self.adaptive_create_url, {"difficulty": 9}, format="json")
        self.assertEqual(res_bad_diff.status_code, status.HTTP_400_BAD_REQUEST)

        res_bad_n = self.client.post(self.adaptive_create_url, {"n_questions": 0}, format="json")
        self.assertEqual(res_bad_n.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("interviewapp.qgen_groq.generate_questions_groq")
    def test_adaptive_session_creation_creates_only_first_question(self, mock_groq):
        mock_groq.return_value = [
            {
                "text": "Explain Python GIL and its impact on CPU-bound threads.",
                "keywords": "gil,threads,multiprocessing",
                "difficulty": 3,
                "type": "reasoning",
            }
        ]
        self._auth_a()
        res = self.client.post(
            self.adaptive_create_url,
            {
                "role": "tech",
                "job_role": "Python Engineer",
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
        self.assertEqual(session.answers.filter(processed=False).count(), 1)
        self.assertEqual(SessionQuestion.objects.filter(session=session).count(), 1)

    @patch("interviewapp.qgen_groq.generate_questions_groq")
    @patch("interviewapp.qgen_groq.generate_follow_up_question_groq")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_full_adaptive_lifecycle_followup_next_main_final_followup_and_summary(
        self, mock_analyze, mock_followup, mock_main_q
    ):
        mock_main_q.side_effect = [
            [{"text": "Main Q1: Explain database indexing.", "keywords": "index,btree", "difficulty": 3, "type": "reasoning"}],
            [{"text": "Main Q2: Explain transaction isolation levels.", "keywords": "acid,isolation", "difficulty": 3, "type": "reasoning"}],
        ]
        mock_followup.side_effect = [
            {"text": "Follow-up Q1: When do indexes hurt write performance?", "keywords": "write,overhead", "difficulty": 3, "type": "reasoning"},
            {"text": "Follow-up Q2: How does MVCC prevent dirty reads?", "keywords": "mvcc,snapshot", "difficulty": 3, "type": "reasoning"},
        ]
        # Q1=55 (follow_up) -> FU1=60 (next_main) -> Q2=55 (final follow_up) -> FU2=80 (completed)
        mock_analyze.side_effect = [
            {"score": 55, "feedback": "Partial answer.", "improvement_tips": ["Add trade-offs"], "resume_grounding": None},
            {"score": 60, "feedback": "Good follow-up.", "improvement_tips": [], "resume_grounding": None},
            {"score": 55, "feedback": "Partial answer on isolation.", "improvement_tips": ["Mention MVCC"], "resume_grounding": None},
            {"score": 80, "feedback": "Strong MVCC explanation.", "improvement_tips": [], "resume_grounding": None},
        ]

        self._auth_a()
        create_res = self.client.post(
            self.adaptive_create_url,
            {"role": "tech", "job_role": "Backend Engineer", "difficulty": 3, "n_questions": 2},
            format="json",
        )
        self.assertEqual(create_res.status_code, status.HTTP_201_CREATED)
        sid = create_res.data["session"]["id"]
        submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": sid})

        # 1. Submit Main Q1 (score=55) -> Follow-up Q1
        r1 = self.client.post(submit_url, {"answer_text": "Indexes speed up reads."}, format="json")
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertFalse(r1.data["is_session_completed"])
        self.assertEqual(r1.data["next_question_kind"], "follow_up")
        self.assertEqual(r1.data["main_questions_count"], 1)
        self.assertEqual(r1.data["total_interactions"], 2)
        self.assertIn("Follow-up Q1", r1.data["next_question"]["text"])

        # 2. Submit Follow-up Q1 (score=60) -> Must NOT trigger another follow-up; advances to Main Q2
        r2 = self.client.post(submit_url, {"answer_text": "Writes update B-tree nodes."}, format="json")
        self.assertEqual(r2.status_code, status.HTTP_200_OK)
        self.assertFalse(r2.data["is_session_completed"])
        self.assertEqual(r2.data["next_question_kind"], "main")
        self.assertEqual(r2.data["main_questions_count"], 2)
        self.assertEqual(r2.data["total_interactions"], 3)
        self.assertTrue(r2.data["answer"]["is_follow_up"])
        self.assertIsNotNone(r2.data["answer"]["parent_answer_id"])

        # 3. Submit Final Main Q2 (score=55) -> Receives its 1 permitted follow-up
        r3 = self.client.post(submit_url, {"answer_text": "Read committed and serializable."}, format="json")
        self.assertEqual(r3.status_code, status.HTTP_200_OK)
        self.assertFalse(r3.data["is_session_completed"])
        self.assertEqual(r3.data["next_question_kind"], "follow_up")
        self.assertEqual(r3.data["main_questions_count"], 2)
        self.assertEqual(r3.data["total_interactions"], 4)

        # 4. Submit Final Follow-up Q2 (score=80) -> Session completes
        r4 = self.client.post(submit_url, {"answer_text": "MVCC keeps row versions."}, format="json")
        self.assertEqual(r4.status_code, status.HTTP_200_OK)
        self.assertTrue(r4.data["is_session_completed"])
        self.assertIsNone(r4.data["next_question"])
        self.assertIsNone(r4.data["next_question_kind"])
        self.assertEqual(r4.data["main_questions_count"], 2)
        self.assertEqual(r4.data["total_interactions"], 4)

        # 5. Summary & PDF report compatibility
        summary_url = reverse("api_v1:session_summary", kwargs={"pk": sid})
        with patch("interviewapp.services.session_service.generate_session_suggestions", return_value={
            "strengths": ["Clear"], "improvements": ["More depth"], "overall_tip": "Good", "resources": []
        }), patch("interviewapp.services.session_service.generate_expected_answer", return_value="Model answer"):
            sum_res = self.client.get(summary_url)
        self.assertEqual(sum_res.status_code, status.HTTP_200_OK)
        self.assertEqual(sum_res.data["session"]["main_questions_count"], 2)
        self.assertEqual(sum_res.data["session"]["total_questions"], 4)
        self.assertEqual(len(sum_res.data["answers"]), 4)
        self.assertEqual(
            [a["is_follow_up"] for a in sum_res.data["answers"]],
            [False, True, False, True],
        )

        report_url = reverse("api_v1:session_report_download", kwargs={"pk": sid})
        pdf_res = self.client.get(report_url)
        self.assertEqual(pdf_res.status_code, status.HTTP_200_OK)
        self.assertEqual(pdf_res["Content-Type"], "application/pdf")

    @patch("interviewapp.qgen_groq.generate_questions_groq")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_adaptive_skip_never_triggers_followup_and_adapts_difficulty(self, mock_analyze, mock_main_q):
        mock_main_q.side_effect = [
            [{"text": "Q1 at level 3", "keywords": "a", "difficulty": 3, "type": "reasoning"}],
            [{"text": "Q2 at level 2", "keywords": "b", "difficulty": 2, "type": "reasoning"}],
        ]
        self._auth_a()
        create_res = self.client.post(
            self.adaptive_create_url,
            {"role": "tech", "job_role": "Backend", "difficulty": 3, "n_questions": 2},
            format="json",
        )
        sid = create_res.data["session"]["id"]
        skip_url = reverse("api_v1:session_adaptive_question_skip", kwargs={"pk": sid})

        # Skip Q1 -> no follow-up, next_main at difficulty 2
        s1 = self.client.post(skip_url, {}, format="json")
        self.assertEqual(s1.status_code, status.HTTP_200_OK)
        self.assertFalse(s1.data["is_session_completed"])
        self.assertEqual(s1.data["answer"]["answer_text"], "[Skipped]")
        self.assertEqual(s1.data["next_question_kind"], "main")
        self.assertEqual(s1.data["next_question"]["difficulty"], 2)

        # Skip Q2 -> session completes
        s2 = self.client.post(skip_url, {}, format="json")
        self.assertEqual(s2.status_code, status.HTTP_200_OK)
        self.assertTrue(s2.data["is_session_completed"])
        self.assertIsNone(s2.data["next_question"])
        mock_analyze.assert_not_called()

    @patch("interviewapp.qgen_groq.generate_questions_groq")
    @patch("interviewapp.qgen_groq.generate_follow_up_question_groq")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_idempotent_retry_and_recovery_without_duplicate_evaluation(
        self, mock_analyze, mock_followup, mock_main_q
    ):
        mock_main_q.return_value = [
            {"text": "Main Q1: Explain caching.", "keywords": "cache,ttl", "difficulty": 3, "type": "reasoning"}
        ]
        mock_followup.return_value = {
            "text": "Follow-up Q1: How do you handle cache invalidation?",
            "keywords": "invalidation,ttl",
            "difficulty": 3,
            "type": "reasoning",
        }
        mock_analyze.return_value = {
            "score": 55,
            "feedback": "Good start.",
            "improvement_tips": [],
            "resume_grounding": None,
        }

        self._auth_a()
        create_res = self.client.post(
            self.adaptive_create_url,
            {"role": "tech", "job_role": "Backend", "difficulty": 3, "n_questions": 2},
            format="json",
        )
        sid = create_res.data["session"]["id"]
        session = InterviewSession.objects.get(id=sid)
        ans1 = session.answers.get(index=1)
        submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": sid})

        # First submit evaluates ans1 and creates follow-up ans2
        r1 = self.client.post(
            submit_url,
            {"answer_id": ans1.id, "answer_text": "Redis caches hot keys."},
            format="json",
        )
        self.assertEqual(r1.status_code, status.HTTP_200_OK)
        self.assertEqual(mock_analyze.call_count, 1)
        self.assertEqual(mock_followup.call_count, 1)

        # Retry with same answer_id -> returns exact same next_question without re-evaluating or regenerating
        r_retry = self.client.post(
            submit_url,
            {"answer_id": ans1.id, "answer_text": "Redis caches hot keys."},
            format="json",
        )
        self.assertEqual(r_retry.status_code, status.HTTP_200_OK)
        self.assertEqual(r_retry.data["next_question"]["id"], r1.data["next_question"]["id"])
        self.assertEqual(mock_analyze.call_count, 1)
        self.assertEqual(mock_followup.call_count, 1)
        self.assertEqual(session.answers.count(), 2)

    @patch("interviewapp.qgen_groq.generate_follow_up_question_groq")
    def test_recovery_when_answer_evaluated_but_next_question_missing(self, mock_followup):
        mock_followup.return_value = {
            "text": "Recovered Follow-up Q1",
            "keywords": "recovery",
            "difficulty": 3,
            "type": "reasoning",
        }
        session = InterviewSession.objects.create(
            user=self.user_a,
            role="tech",
            job_role="Backend",
            difficulty=3,
            state="adaptive",
            max_main_questions=3,
            total_questions=1,
            current_index=1,
        )
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain queues.", signature="rec-q1"
        )
        ans1 = Answer.objects.create(
            session=session,
            question=q1,
            index=1,
            answer_text="Queues decouple producers and consumers.",
            score=55,
            processed=True,
            processing_state="processed",
        )
        SessionQuestion.objects.create(session=session, question=q1, order=1, asked=True)

        self._auth_a()
        submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": session.id})
        res = self.client.post(
            submit_url,
            {"answer_id": ans1.id, "answer_text": "Queues decouple producers and consumers."},
            format="json",
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["next_question_kind"], "follow_up")
        self.assertEqual(res.data["next_question"]["text"], "Recovered Follow-up Q1")
        self.assertEqual(session.answers.count(), 2)

        # Calling advance again is idempotent
        replay = advance_adaptive_session_from_answer(session, ans1)
        self.assertTrue(replay.idempotent_replay)
        self.assertEqual(session.answers.count(), 2)

    def test_adaptive_endpoints_enforce_ownership_state_and_conflict(self):
        session = InterviewSession.objects.create(
            user=self.user_a,
            role="tech",
            job_role="Backend",
            difficulty=3,
            state="adaptive",
            max_main_questions=2,
            total_questions=1,
            current_index=1,
        )
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain HTTP.", signature="own-q1"
        )
        ans1 = Answer.objects.create(
            session=session,
            question=q1,
            index=1,
            processed=False,
            processing_state="processing",
            claim_token="active-claim",
            claimed_at=timezone.now(),
        )

        submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": session.id})

        # User B gets 404
        self._auth_b()
        res_other = self.client.post(submit_url, {"answer_text": "Hi"}, format="json")
        self.assertEqual(res_other.status_code, status.HTTP_404_NOT_FOUND)

        # Active in-flight claim returns 409 Conflict
        self._auth_a()
        res_conflict = self.client.post(
            submit_url, {"answer_id": ans1.id, "answer_text": "HTTP is stateless."}, format="json"
        )
        self.assertEqual(res_conflict.status_code, status.HTTP_409_CONFLICT)

        # Non-adaptive session rejected with 400
        fixed_session = InterviewSession.objects.create(
            user=self.user_a, role="tech", job_role="Backend", state="in_progress", total_questions=1
        )
        fixed_submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": fixed_session.id})
        res_wrong_mode = self.client.post(fixed_submit_url, {"answer_text": "Test"}, format="json")
        self.assertEqual(res_wrong_mode.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("interviewapp.qgen_groq.generate_follow_up_question_groq", side_effect=RuntimeError("Groq down"))
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_groq_followup_failure_falls_back_safely_without_losing_answer(self, mock_analyze, _mock_fu):
        mock_analyze.return_value = {
            "score": 55,
            "feedback": "Partial answer.",
            "improvement_tips": [],
            "resume_grounding": None,
        }
        session = InterviewSession.objects.create(
            user=self.user_a,
            role="tech",
            job_role="Backend",
            difficulty=3,
            state="adaptive",
            max_main_questions=2,
            total_questions=1,
            current_index=1,
        )
        q1 = GeneratedQuestion.objects.create(
            role="tech", difficulty=3, text="Explain REST.", signature="fb-q1"
        )
        ans1 = Answer.objects.create(session=session, question=q1, index=1)

        self._auth_a()
        submit_url = reverse("api_v1:session_adaptive_answer_submit", kwargs={"pk": session.id})
        res = self.client.post(submit_url, {"answer_text": "REST uses HTTP verbs."}, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["next_question_kind"], "follow_up")
        ans1.refresh_from_db()
        self.assertTrue(ans1.processed)
        self.assertEqual(ans1.score, 55)
        self.assertEqual(session.answers.count(), 2)

