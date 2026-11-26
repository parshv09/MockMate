"""
Unit and regression tests for Hybrid Adaptive Interview Milestone 1 (Backend Foundation).
"""

from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import TestCase

from interviewapp.models import (
    Answer,
    GeneratedQuestion,
    InterviewSession,
    SessionQuestion,
)
from interviewapp.services.adaptive_service import (
    AdaptivePolicy,
    AdaptiveStepInput,
    EXPLICIT_SKIP_TEXT,
    TRANSCRIPTION_FAILED_TEXT,
    compute_next_main_difficulty,
    create_adaptive_session,
    decide_next_adaptive_step,
    is_follow_up_eligible,
    is_hr_role,
    is_skipped_answer,
)
from interviewapp.services.answer_service import (
    skip_candidate_question,
    submit_candidate_answer,
)

User = get_user_model()


class AdaptiveModelPersistenceTests(TestCase):
    """Tests for additive InterviewSession and Answer fields and relationships."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="adaptive_model_user",
            email="adaptive_model@example.com",
            password="Password123!",
        )
        self.session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Engineer",
            difficulty=3,
            state="adaptive",
            max_main_questions=5,
            total_questions=1,
            current_index=1,
        )
        self.q_main = GeneratedQuestion.objects.create(
            role="tech",
            difficulty=3,
            text="Explain database indexing.",
            keywords="btree,index,query",
            signature="adaptive-test-q-main",
        )
        self.q_follow = GeneratedQuestion.objects.create(
            role="tech",
            difficulty=3,
            text="When can an index hurt write throughput?",
            keywords="write,overhead,btree",
            signature="adaptive-test-q-follow",
        )

    def test_main_and_followup_parent_relationship_and_sequential_indices(self):
        main_ans = Answer.objects.create(
            session=self.session,
            question=self.q_main,
            parent_answer=None,
            index=1,
            processed=True,
            score=60,
        )
        follow_ans = Answer.objects.create(
            session=self.session,
            question=self.q_follow,
            parent_answer=main_ans,
            index=2,
            processed=False,
        )

        self.assertEqual(self.session.state, "adaptive")
        self.assertEqual(self.session.max_main_questions, 5)
        self.assertIsNone(main_ans.parent_answer)
        self.assertEqual(follow_ans.parent_answer, main_ans)
        self.assertEqual(list(main_ans.follow_ups.all()), [follow_ans])
        self.assertEqual(
            list(self.session.answers.order_by("index").values_list("index", flat=True)),
            [1, 2],
        )

        # Sequential index uniqueness within a session remains enforced
        with self.assertRaises(IntegrityError):
            Answer.objects.create(
                session=self.session,
                question=self.q_follow,
                parent_answer=main_ans,
                index=2,
            )

    def test_parent_answer_deletion_preserves_followup_with_set_null(self):
        main_ans = Answer.objects.create(
            session=self.session,
            question=self.q_main,
            parent_answer=None,
            index=1,
        )
        follow_ans = Answer.objects.create(
            session=self.session,
            question=self.q_follow,
            parent_answer=main_ans,
            index=2,
        )
        main_ans.delete()
        follow_ans.refresh_from_db()
        self.assertIsNone(follow_ans.parent_answer)


class AdaptiveDecisionEngineTests(TestCase):
    """Pure deterministic decision engine tests (no Groq calls, zero DB queries)."""

    @staticmethod
    def _make_step_input(
        *,
        role="tech",
        max_main_questions=3,
        main_count=1,
        current_difficulty=3,
        score=50.0,
        is_skipped=False,
        is_follow_up=False,
        has_followup=False,
        answer_id=101,
    ):
        return AdaptiveStepInput(
            role=role,
            max_main_questions=max_main_questions,
            main_count=main_count,
            current_difficulty=current_difficulty,
            score=score,
            is_skipped=is_skipped,
            is_follow_up=is_follow_up,
            has_followup=has_followup,
            answer_id=answer_id,
        )

    def test_decision_engine_performs_zero_database_queries(self):
        step_input = self._make_step_input(score=60, current_difficulty=3, main_count=1)
        with self.assertNumQueries(0):
            decision = decide_next_adaptive_step(step_input)
        self.assertEqual(decision.action, "follow_up")
        self.assertEqual(decision.next_difficulty, 3)
        self.assertEqual(decision.parent_answer_id, 101)

    def test_followup_triggered_for_scores_in_40_to_75_band(self):
        for boundary_score in (40, 58, 74.9):
            step_input = self._make_step_input(
                score=boundary_score,
                current_difficulty=3,
                main_count=1,
                answer_id=200 + int(boundary_score),
            )
            with self.assertNumQueries(0):
                decision = decide_next_adaptive_step(step_input)
            self.assertEqual(decision.action, "follow_up")
            self.assertEqual(decision.next_difficulty, 3)
            self.assertEqual(decision.parent_answer_id, step_input.answer_id)

    def test_skipped_answer_detection_distinguishes_explicit_skip_from_other_texts(self):
        self.assertTrue(is_skipped_answer(EXPLICIT_SKIP_TEXT))
        self.assertTrue(is_skipped_answer("  [Skipped]  "))

        # Empty, transcription failure, and legitimate candidate text must NOT be classified as explicit skips
        self.assertFalse(is_skipped_answer(""))
        self.assertFalse(is_skipped_answer("   "))
        self.assertFalse(is_skipped_answer(TRANSCRIPTION_FAILED_TEXT))
        self.assertFalse(is_skipped_answer("No answer provided"))
        self.assertFalse(is_skipped_answer("I would use a hash map for O(1) lookup."))

    def test_no_followup_for_skipped_answer_and_difficulty_decreases(self):
        step_input = self._make_step_input(
            current_difficulty=3,
            score=0,
            is_skipped=is_skipped_answer(EXPLICIT_SKIP_TEXT),
            main_count=1,
        )
        eligible, reason = is_follow_up_eligible(
            is_follow_up=step_input.is_follow_up,
            has_followup=step_input.has_followup,
            is_skipped=step_input.is_skipped,
            score=step_input.score,
        )
        self.assertFalse(eligible)
        self.assertEqual(reason, "skipped_answer")

        # Even with a custom policy allowing 0, skipped answers are never eligible
        permissive_policy = AdaptivePolicy(follow_up_min_score=0.0, follow_up_max_score=100.0)
        eligible_custom, _ = is_follow_up_eligible(
            is_follow_up=False,
            has_followup=False,
            is_skipped=True,
            score=0,
            policy=permissive_policy,
        )
        self.assertFalse(eligible_custom)

        with self.assertNumQueries(0):
            decision = decide_next_adaptive_step(step_input)
        self.assertEqual(decision.action, "next_main")
        self.assertEqual(decision.next_difficulty, 2)
        self.assertIsNone(decision.parent_answer_id)

    def test_no_followup_after_followup_and_no_second_followup_for_same_main(self):
        # Follow-up answer itself cannot trigger another follow-up
        after_followup = self._make_step_input(
            current_difficulty=3,
            score=55,
            is_follow_up=True,
            has_followup=False,
            main_count=1,
        )
        with self.assertNumQueries(0):
            decision_after_followup = decide_next_adaptive_step(after_followup)
        self.assertEqual(decision_after_followup.action, "next_main")
        self.assertEqual(decision_after_followup.next_difficulty, 3)
        self.assertIsNone(decision_after_followup.parent_answer_id)

        # Main answer that already has a follow-up cannot receive a second one
        eligible_again, reason = is_follow_up_eligible(
            is_follow_up=False,
            has_followup=True,
            is_skipped=False,
            score=55,
        )
        self.assertFalse(eligible_again)
        self.assertEqual(reason, "follow_up_already_used")

    def test_final_main_question_can_receive_followup_then_completes(self):
        final_main = self._make_step_input(
            current_difficulty=4,
            score=60,
            is_follow_up=False,
            has_followup=False,
            main_count=3,
            max_main_questions=3,
            answer_id=301,
        )
        with self.assertNumQueries(0):
            d1 = decide_next_adaptive_step(final_main)
        self.assertEqual(d1.action, "follow_up")
        self.assertEqual(d1.next_difficulty, 4)
        self.assertEqual(d1.parent_answer_id, 301)

        final_followup = self._make_step_input(
            current_difficulty=4,
            score=60,
            is_follow_up=True,
            has_followup=False,
            main_count=3,
            max_main_questions=3,
            answer_id=302,
        )
        with self.assertNumQueries(0):
            d2 = decide_next_adaptive_step(final_followup)
        self.assertEqual(d2.action, "completed")
        self.assertIsNone(d2.parent_answer_id)

    def test_completion_when_final_main_outside_followup_band_and_budget_enforced(self):
        final_main = self._make_step_input(
            current_difficulty=3,
            score=85,
            main_count=3,
            max_main_questions=3,
        )
        with self.assertNumQueries(0):
            decision = decide_next_adaptive_step(final_main)
        self.assertEqual(decision.action, "completed")
        self.assertEqual(decision.reason, "max_main_questions_reached")

        # Even if main_count exceeds max_main_questions, never returns next_main
        over_budget = self._make_step_input(
            current_difficulty=3,
            score=85,
            main_count=4,
            max_main_questions=3,
        )
        with self.assertNumQueries(0):
            over_decision = decide_next_adaptive_step(over_budget)
        self.assertEqual(over_decision.action, "completed")

    def test_difficulty_increases_decreases_and_clamps_between_1_and_5(self):
        with self.assertNumQueries(0):
            self.assertEqual(
                compute_next_main_difficulty(role="tech", current_difficulty=4, score=75, is_skipped=False),
                5,
            )
            self.assertEqual(
                compute_next_main_difficulty(role="tech", current_difficulty=5, score=95, is_skipped=False),
                5,
            )
            self.assertEqual(
                compute_next_main_difficulty(role="tech", current_difficulty=2, score=39, is_skipped=False),
                1,
            )
            self.assertEqual(
                compute_next_main_difficulty(role="tech", current_difficulty=1, score=10, is_skipped=False),
                1,
            )

    def test_hr_roles_preserve_difficulty_while_non_hr_adapts(self):
        for hr_variant in ("hr", "HR", "  hr ", "Human Resources", "human resources", "  Human   Resources "):
            self.assertTrue(is_hr_role(hr_variant))
            with self.assertNumQueries(0):
                self.assertEqual(
                    compute_next_main_difficulty(role=hr_variant, current_difficulty=3, score=95, is_skipped=False),
                    3,
                )
                self.assertEqual(
                    compute_next_main_difficulty(role=hr_variant, current_difficulty=3, score=15, is_skipped=False),
                    3,
                )
                self.assertEqual(
                    compute_next_main_difficulty(role=hr_variant, current_difficulty=3, score=0, is_skipped=True),
                    3,
                )

        # Non-HR role still adapts
        self.assertFalse(is_hr_role("tech"))
        with self.assertNumQueries(0):
            self.assertEqual(
                compute_next_main_difficulty(role="tech", current_difficulty=3, score=90, is_skipped=False),
                4,
            )
            self.assertEqual(
                compute_next_main_difficulty(role="tech", current_difficulty=3, score=20, is_skipped=False),
                2,
            )


class AdaptiveSessionCreationAndEvaluationCompatTests(TestCase):
    """Tests for adaptive session initialization and answer_service auto_complete flag."""

    def setUp(self):
        self.user = User.objects.create_user(
            username="adaptive_create_user",
            email="adaptive_create@example.com",
            password="Password123!",
        )

    @patch("interviewapp.qgen_groq.generate_questions_groq")
    def test_create_adaptive_session_creates_only_first_question(self, mock_groq):
        mock_groq.return_value = [
            {
                "text": "Explain Python asyncio event loops.",
                "keywords": "asyncio,event loop,coroutine",
                "difficulty": 4,
                "type": "reasoning",
            }
        ]

        session, created_count = create_adaptive_session(
            user=self.user,
            raw_role="tech",
            job_role="Python Backend Engineer",
            difficulty=4,
            max_main_questions=6,
        )

        self.assertEqual(created_count, 1)
        self.assertEqual(session.state, "adaptive")
        self.assertEqual(session.max_main_questions, 6)
        self.assertEqual(session.total_questions, 1)
        self.assertEqual(session.current_index, 1)
        self.assertFalse(session.completed)

        answers = list(session.answers.all())
        self.assertEqual(len(answers), 1)
        self.assertEqual(answers[0].index, 1)
        self.assertIsNone(answers[0].parent_answer)
        self.assertEqual(answers[0].question.text, "Explain Python asyncio event loops.")
        self.assertEqual(SessionQuestion.objects.filter(session=session).count(), 1)
        mock_groq.assert_called_once()

    @patch("interviewapp.qgen_groq.generate_questions_groq", side_effect=RuntimeError("Groq unavailable"))
    def test_create_adaptive_session_falls_back_to_stub_on_groq_error(self, _mock_groq):
        session, created_count = create_adaptive_session(
            user=self.user,
            raw_role="tech",
            job_role="Data Engineer",
            difficulty=2,
            max_main_questions=4,
        )
        self.assertEqual(created_count, 1)
        self.assertEqual(session.answers.count(), 1)
        self.assertEqual(session.answers.first().question.source, "template")

    def test_create_adaptive_session_validation_errors(self):
        with self.assertRaises(ValueError):
            create_adaptive_session(user=self.user, raw_role="invalid")
        with self.assertRaises(ValueError):
            create_adaptive_session(user=self.user, difficulty=6)
        with self.assertRaises(ValueError):
            create_adaptive_session(user=self.user, max_main_questions=0)

    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_answer_service_auto_complete_false_preserves_in_progress_session(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 60,
            "feedback": "Good start, elaborate on trade-offs.",
            "improvement_tips": ["Add trade-offs"],
            "resume_grounding": None,
        }
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Engineer",
            difficulty=3,
            state="adaptive",
            max_main_questions=5,
            total_questions=1,
            current_index=1,
        )
        q1 = GeneratedQuestion.objects.create(
            role="tech",
            difficulty=3,
            text="Explain CAP theorem.",
            signature="cap-theorem-compat",
        )
        ans1 = Answer.objects.create(session=session, question=q1, index=1)

        evaluated, is_completed = submit_candidate_answer(
            session=session,
            answer_id=ans1.id,
            answer_text="Consistency, availability, partition tolerance.",
            auto_complete=False,
        )
        session.refresh_from_db()

        self.assertTrue(evaluated.processed)
        self.assertEqual(evaluated.score, 60)
        self.assertFalse(is_completed)
        self.assertFalse(session.completed)
        self.assertIsNone(session.completed_at)

    def test_skip_service_auto_complete_false_preserves_in_progress_session(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Engineer",
            difficulty=3,
            state="adaptive",
            max_main_questions=5,
            total_questions=1,
            current_index=1,
        )
        q1 = GeneratedQuestion.objects.create(
            role="tech",
            difficulty=3,
            text="Explain Raft consensus.",
            signature="raft-compat",
        )
        ans1 = Answer.objects.create(session=session, question=q1, index=1)

        skipped, is_completed = skip_candidate_question(
            session=session,
            answer_id=ans1.id,
            auto_complete=False,
        )
        session.refresh_from_db()

        self.assertTrue(skipped.processed)
        self.assertEqual(skipped.answer_text, "[Skipped]")
        self.assertEqual(skipped.score, 0)
        self.assertFalse(is_completed)
        self.assertFalse(session.completed)

