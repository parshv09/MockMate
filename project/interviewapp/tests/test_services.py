"""
Unit test suite for the MockMate service layer:
- session_service
- answer_service
- resume_service
- video_service
- report_service
- template view ownership permissions
"""

from io import BytesIO
from unittest.mock import MagicMock, patch
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import OperationalError
from django.test import TestCase, override_settings
from django.urls import reverse

from interviewapp.models import Answer, GeneratedQuestion, InterviewSession, Resume
from interviewapp.services import (
    build_session_pdf_report,
    create_phase_practice_session,
    create_resume_jd_session,
    create_standard_session,
    end_candidate_session,
    extract_text_from_resume_file,
    finalize_session_video_metrics,
    get_next_unprocessed_answer,
    get_session_summary_data,
    process_video_frame,
    save_and_index_resume,
    skip_candidate_question,
    submit_candidate_answer,
)
from interviewapp.services.video_service import (
    _LUA_FINALIZE_SCRIPT,
    _LUA_INCREMENT_SCRIPT,
    get_redis_client,
)


class MockRedisClient:
    """In-memory mock providing exact Lua script execution semantics for testing."""
    def __init__(self):
        self.hashes = {}
        self.sets = {}
        self.ttls = {}
        self.deleted_keys = []

    def eval(self, script, numkeys, *args):
        if script == _LUA_INCREMENT_SCRIPT:
            stats_key = args[0]
            frames_key = args[1]
            frame_id = args[2]
            d_total = int(args[3])
            d_face = int(args[4])
            d_multiple = int(args[5])
            d_eye = int(args[6])
            d_head = int(args[7])
            ttl = int(args[8])

            h = self.hashes.setdefault(stats_key, {})
            s = self.sets.setdefault(frames_key, set())

            if h.get("finalized") == "1":
                return ["err", "SESSION_FINALIZED"]

            if frame_id != "":
                if frame_id in s:
                    return ["dup", dict(h)]
                s.add(frame_id)
                self.ttls[frames_key] = ttl

            h["backend"] = "redis"
            h["total_frames"] = str(int(h.get("total_frames", 0)) + d_total)
            h["face_present_frames"] = str(int(h.get("face_present_frames", 0)) + d_face)
            h["multiple_faces_frames"] = str(int(h.get("multiple_faces_frames", 0)) + d_multiple)
            h["eye_contact_frames"] = str(int(h.get("eye_contact_frames", 0)) + d_eye)
            h["head_movement_frames"] = str(int(h.get("head_movement_frames", 0)) + d_head)
            self.ttls[stats_key] = ttl
            return ["ok", dict(h)]

        elif script == _LUA_FINALIZE_SCRIPT:
            stats_key = args[0]
            ttl = int(args[1])
            if stats_key not in self.hashes:
                return ["not_found"]

            h = self.hashes[stats_key]
            already = h.get("finalized") == "1"
            h["finalized"] = "1"
            self.ttls[stats_key] = ttl
            status = "already_finalized" if already else "finalized"
            return [status, dict(h)]

        return ["err", "unknown script"]

    def delete(self, key):
        self.deleted_keys.append(key)
        self.hashes.pop(key, None)
        self.sets.pop(key, None)
        self.ttls.pop(key, None)


class TestServiceLayer(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="service_tester",
            email="tester@example.com",
            password="StrongPassword123!",
            first_name="Service",
            last_name="Tester",
        )
        self.other_user = User.objects.create_user(
            username="unauthorized_user",
            email="other@example.com",
            password="OtherPassword123!",
            first_name="Other",
            last_name="User",
        )

    # -------------------------------------------------------------------------
    # Session Service Tests
    # -------------------------------------------------------------------------
    @override_settings(RAG_ENABLED=False)
    @patch("interviewapp.services.session_service.generate_questions_groq")
    def test_create_standard_session(self, mock_groq):
        mock_groq.return_value = [
            {"text": "Explain Python GIL.", "difficulty": 2, "keywords": "python,gil"},
            {"text": "How do Python decorators work?", "difficulty": 2, "keywords": "python,decorators"},
            {"text": "What is MRO in Python?", "difficulty": 2, "keywords": "python,mro"},
        ]

        session, created_count = create_standard_session(
            user=self.user,
            raw_role="tech",
            job_role="Python Developer",
            difficulty=2,
            n_questions=3,
        )

        self.assertEqual(session.user, self.user)
        self.assertEqual(session.role, "tech")
        self.assertEqual(session.job_role, "Python Developer")
        self.assertEqual(created_count, 3)
        self.assertEqual(session.total_questions, 3)
        self.assertEqual(session.answers.count(), 3)
        self.assertFalse(session.completed)

    @override_settings(RAG_ENABLED=True)
    @patch("interviewapp.services.session_service.generate_questions_with_rag")
    def test_create_standard_session_rag(self, mock_rag):
        mock_rag.return_value = [
            {"text": "Explain RAG architecture in Python.", "difficulty": 3, "keywords": "rag,python"},
            {"text": "Explain vector embeddings indexing.", "difficulty": 3, "keywords": "vector,embeddings"},
        ]

        session, created_count = create_standard_session(
            user=self.user,
            raw_role="tech",
            job_role="AI Engineer",
            difficulty=3,
            n_questions=2,
        )

        self.assertEqual(session.user, self.user)
        self.assertEqual(created_count, 2)
        self.assertEqual(session.answers.count(), 2)

    @override_settings(RAG_ENABLED=False)
    @patch("interviewapp.services.session_service.generate_resume_jd_questions_groq")
    def test_create_resume_jd_session_existing_resume(self, mock_groq):
        mock_groq.return_value = [
            {"text": "Explain Django ORM optimizations from your resume.", "difficulty": 3, "keywords": "django,orm"},
            {"text": "How did you scale PostgreSQL at your previous job?", "difficulty": 3, "keywords": "postgres,scale"},
        ]

        existing_resume = Resume.objects.create(
            user=self.user,
            title="Senior Backend Resume",
            extracted_text="Experienced Django and PostgreSQL developer."
        )

        session, count = create_resume_jd_session(
            user=self.user,
            resume_obj=existing_resume,
            job_description="Seeking a Senior Django Engineer.",
            difficulty=3,
            n_questions=2,
        )

        self.assertIsNotNone(session)
        self.assertEqual(session.user, self.user)
        self.assertEqual(session.resume, existing_resume)
        self.assertEqual(count, 2)
        self.assertEqual(session.answers.count(), 2)
        self.assertTrue(session.job_role.startswith("Job Match:"))

    @override_settings(RAG_ENABLED=False)
    @patch("interviewapp.services.resume_service.index_resume")
    @patch("interviewapp.services.session_service.generate_resume_jd_questions_groq")
    def test_create_resume_jd_session_new_uploaded_resume(self, mock_groq, mock_index):
        mock_groq.return_value = [
            {"text": "Tell me about your Python experience.", "difficulty": 2, "keywords": "python"},
            {"text": "Explain your API design philosophy.", "difficulty": 2, "keywords": "api,design"},
        ]

        mock_file = SimpleUploadedFile("resume.txt", b"Jane Developer - 4 years backend experience.", content_type="text/plain")

        session, count = create_resume_jd_session(
            user=self.user,
            resume_obj=None,
            resume_file=mock_file,
            resume_title="Jane Uploaded Resume",
            job_description="Backend Python Role",
            difficulty=2,
            n_questions=2,
        )

        self.assertIsNotNone(session)
        self.assertIsNotNone(session.resume)
        self.assertIn("Jane Developer", session.resume.extracted_text)
        self.assertEqual(count, 2)
        self.assertEqual(session.answers.count(), 2)

    def test_get_next_unprocessed_answer(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Developer",
            total_questions=2,
        )
        q1 = GeneratedQuestion.objects.create(text="Question 1", role="tech", difficulty=2, signature="sig1")
        q2 = GeneratedQuestion.objects.create(text="Question 2", role="tech", difficulty=2, signature="sig2")
        a1 = Answer.objects.create(session=session, question=q1, index=1, processed=False)
        a2 = Answer.objects.create(session=session, question=q2, index=2, processed=False)

        next_ans = get_next_unprocessed_answer(session)
        self.assertIsNotNone(next_ans)
        self.assertEqual(next_ans.id, a1.id)
        self.assertEqual(session.current_index, 1)

        # Mark first processed, second should be returned next
        a1.processed = True
        a1.save()

        next_ans2 = get_next_unprocessed_answer(session)
        self.assertIsNotNone(next_ans2)
        self.assertEqual(next_ans2.id, a2.id)
        self.assertEqual(session.current_index, 2)

    def test_get_session_summary_data_aggregates(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Full-Stack Developer",
            total_questions=2,
            completed=True,
        )
        q1 = GeneratedQuestion.objects.create(text="Explain REST APIs.", role="tech", difficulty=2, signature="rest_q1")
        q2 = GeneratedQuestion.objects.create(text="Explain WebSockets.", role="tech", difficulty=2, signature="ws_q2")
        Answer.objects.create(
            session=session,
            question=q1,
            index=1,
            answer_text="REST uses HTTP methods.",
            score=80.0,
            feedback="Good answer.",
            processed=True,
        )
        Answer.objects.create(
            session=session,
            question=q2,
            index=2,
            answer_text="WebSockets provide full-duplex TCP channels.",
            score=60.0,
            feedback="Acceptable answer.",
            processed=True,
        )

        data = get_session_summary_data(session)
        self.assertEqual(data["avg"], 70.0)
        self.assertEqual(data["content_quality_score"], 70.0)
        self.assertEqual(data["completion_rate"], 100)
        session.refresh_from_db()
        self.assertEqual(session.total_score, 70.0)

    # -------------------------------------------------------------------------
    # Answer Service Tests
    # -------------------------------------------------------------------------
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_submit_candidate_answer_and_complete(self, mock_analyze):
        mock_analyze.return_value = {
            "score": 85,
            "feedback": "Clear explanation of concepts.",
            "improvement_tips": ["Mention edge cases."],
            "resume_grounding": None,
        }

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Developer",
            total_questions=1,
        )
        q = GeneratedQuestion.objects.create(text="Explain REST APIs.", role="tech", difficulty=2, signature="rest1")
        ans = Answer.objects.create(session=session, question=q, index=1, processed=False)

        updated_ans, is_completed = submit_candidate_answer(
            session=session,
            answer_id=ans.id,
            answer_text="REST APIs use standard HTTP verbs.",
        )

        self.assertTrue(updated_ans.processed)
        self.assertEqual(updated_ans.score, 85)
        self.assertEqual(updated_ans.feedback, "Clear explanation of concepts.")
        self.assertTrue(is_completed)

        session.refresh_from_db()
        self.assertTrue(session.completed)
        self.assertIsNotNone(session.completed_at)

    @patch("interviewapp.services.answer_service.transcribe_audio")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_submit_candidate_audio_answer_with_whisper(self, mock_analyze, mock_transcribe):
        mock_transcribe.return_value = "This is a transcribed voice answer."
        mock_analyze.return_value = {
            "score": 75,
            "feedback": "Good voice answer.",
            "improvement_tips": [],
            "resume_grounding": None,
        }

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="DevOps",
            total_questions=1,
        )
        q = GeneratedQuestion.objects.create(text="Explain Docker.", role="tech", difficulty=2, signature="dock1")
        ans = Answer.objects.create(session=session, question=q, index=1, processed=False)

        audio_file = SimpleUploadedFile("audio.wav", b"fake audio bytes", content_type="audio/wav")

        updated_ans, is_completed = submit_candidate_answer(
            session=session,
            answer_id=ans.id,
            answer_text="",
            audio_file=audio_file,
        )

        mock_transcribe.assert_called_once()
        self.assertEqual(updated_ans.answer_text, "This is a transcribed voice answer.")
        self.assertEqual(updated_ans.score, 75)
        self.assertTrue(updated_ans.processed)
        self.assertTrue(is_completed)

    @patch("interviewapp.services.answer_service.transcribe_audio")
    @patch("interviewapp.services.answer_service.analyze_transcript")
    def test_submit_candidate_answer_audio_cleanup_on_failure(self, mock_analyze, mock_transcribe):
        mock_transcribe.return_value = "Mocked transcribed text"
        mock_analyze.side_effect = RuntimeError("Evaluation LLM offline.")

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="DevOps",
            total_questions=1,
        )
        q = GeneratedQuestion.objects.create(text="Explain Kubernetes.", role="tech", difficulty=3, signature="k8s1")
        ans = Answer.objects.create(session=session, question=q, index=1, processed=False)

        audio_file = SimpleUploadedFile("temp_audio.wav", b"temporary audio content", content_type="audio/wav")

        with self.assertRaises(RuntimeError):
            submit_candidate_answer(
                session=session,
                answer_id=ans.id,
                answer_text="",
                audio_file=audio_file,
            )

        ans.refresh_from_db()
        self.assertFalse(ans.processed)
        # Verify the answer record audio_file was reset
        self.assertFalse(bool(ans.audio_file))

    def test_skip_candidate_question(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Developer",
            total_questions=1,
        )
        q = GeneratedQuestion.objects.create(text="Explain Paxos algorithm.", role="tech", difficulty=3, signature="paxos1")
        ans = Answer.objects.create(session=session, question=q, index=1, processed=False)

        skipped_ans, is_completed = skip_candidate_question(session, answer_id=ans.id)
        self.assertIsNotNone(skipped_ans)
        self.assertTrue(skipped_ans.processed)
        self.assertEqual(skipped_ans.score, 0)
        self.assertEqual(skipped_ans.answer_text, "[Skipped]")
        self.assertTrue(is_completed)

        session.refresh_from_db()
        self.assertTrue(session.completed)

    def test_skip_already_completed_session(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Developer",
            total_questions=1,
            completed=True,
        )
        ans, is_completed = skip_candidate_question(session)
        self.assertIsNone(ans)
        self.assertTrue(is_completed)

    def test_end_candidate_session(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="DevOps",
            total_questions=3,
        )
        end_candidate_session(session)
        session.refresh_from_db()
        self.assertTrue(session.completed)
        self.assertIsNotNone(session.completed_at)

    # -------------------------------------------------------------------------
    # Resume Service Tests
    # -------------------------------------------------------------------------
    @patch("interviewapp.services.resume_service.index_resume")
    def test_extract_text_and_save_resume(self, mock_index):
        mock_file = SimpleUploadedFile("resume.txt", b"Jane Doe - Software Engineer with 5 years experience.", content_type="text/plain")
        extracted = extract_text_from_resume_file(mock_file)
        self.assertIn("Jane Doe", extracted)

        resume_obj = save_and_index_resume(
            user=self.user,
            file_obj=mock_file,
            title="Jane Doe Resume",
            raw_text="",
        )
        self.assertIsNotNone(resume_obj)
        self.assertEqual(resume_obj.user, self.user)
        self.assertIn("Jane Doe", resume_obj.extracted_text)

    # -------------------------------------------------------------------------
    # Video Service Tests
    # -------------------------------------------------------------------------
    @patch("interviewapp.services.video_service.generate_video_behavior_feedback")
    @patch("interviewapp.services.video_service.analyze_eye_contact_and_head")
    @patch("interviewapp.services.video_service.count_faces")
    def test_process_video_frame_and_finalize(self, mock_count, mock_behavior, mock_feedback):
        mock_count.return_value = 1
        mock_behavior.return_value = {"eye_contact": True, "head_movement": False}
        mock_feedback.return_value = {
            "summary": "Good eye contact and steady composure.",
            "strengths": ["Consistent gaze"],
            "improvements": ["Maintain natural posture"],
        }

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        result = process_video_frame(session.id, dummy_frame)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["faces"], 1)
        self.assertTrue(result["eye_contact"])

        summary, feedback = finalize_session_video_metrics(session)
        session.refresh_from_db()
        self.assertIsNotNone(session.video_stats_json)
        self.assertGreaterEqual(session.video_stats_json.get("total_frames", 0), 1)

    # -------------------------------------------------------------------------
    # Report Service Tests
    # -------------------------------------------------------------------------
    def test_build_session_pdf_report(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Full-Stack Developer",
            total_questions=1,
            completed=True,
        )
        q = GeneratedQuestion.objects.create(text="What is React virtual DOM?", role="tech", difficulty=2, signature="vdom1")
        Answer.objects.create(
            session=session,
            question=q,
            index=1,
            answer_text="Virtual DOM is a lightweight copy of the real DOM in memory.",
            score=90,
            feedback="Great concise definition.",
            processed=True,
        )

        pdf_buffer = build_session_pdf_report(session)
        self.assertIsInstance(pdf_buffer, BytesIO)
        content = pdf_buffer.getvalue()
        self.assertTrue(len(content) > 0)
        self.assertTrue(content.startswith(b"%PDF"))

    # -------------------------------------------------------------------------
    # Template View Ownership & Security Permission Tests
    # -------------------------------------------------------------------------
    def test_template_view_ownership_permissions(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Security Engineer",
            total_questions=1,
        )
        q = GeneratedQuestion.objects.create(text="Explain SQL injection.", role="tech", difficulty=2, signature="sqli1")
        ans = Answer.objects.create(session=session, question=q, index=1, processed=False)

        # Login as other_user (unauthorized for self.user's session)
        self.client.force_login(self.other_user)

        # 1. next_question
        resp = self.client.get(reverse("interviewapp:next_question", kwargs={"session_id": session.id}))
        self.assertEqual(resp.status_code, 403)

        # 2. submit_answer
        resp = self.client.post(
            reverse("interviewapp:submit_answer", kwargs={"session_id": session.id}),
            {"answer_id": ans.id, "answer_text": "Unauthorized answer."}
        )
        self.assertEqual(resp.status_code, 403)

        # 3. skip_question
        resp = self.client.post(reverse("interviewapp:skip_question", kwargs={"session_id": session.id}))
        self.assertEqual(resp.status_code, 403)

        # 4. end_session
        resp = self.client.post(reverse("interviewapp:end_session", kwargs={"session_id": session.id}))
        self.assertEqual(resp.status_code, 403)

        # 5. session_summary
        resp = self.client.get(reverse("interviewapp:session_summary", kwargs={"session_id": session.id}))
        self.assertEqual(resp.status_code, 403)

        # 6. download_report
        resp = self.client.get(reverse("interviewapp:download_report", kwargs={"session_id": session.id}))
        self.assertEqual(resp.status_code, 403)

        # 7. delete_session
        resp = self.client.post(reverse("interviewapp:delete_session", kwargs={"session_id": session.id}))
        self.assertEqual(resp.status_code, 403)

        # 8. upload_frame
        dummy_frame = SimpleUploadedFile("frame.jpg", b"fake frame bytes", content_type="image/jpeg")
        resp = self.client.post(
            reverse("interviewapp:upload_frame"),
            {"session_id": session.id, "frame": dummy_frame}
        )
        self.assertEqual(resp.status_code, 403)

    # -------------------------------------------------------------------------
    # Video Service Concurrency & Redis Tests
    # -------------------------------------------------------------------------
    @patch("interviewapp.services.video_service.get_redis_client")
    def test_atomic_redis_increment(self, mock_get_redis):
        fake_redis = MockRedisClient()
        mock_get_redis.return_value = fake_redis

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        result = process_video_frame(session.id, dummy_frame, frame_id="f1")
        self.assertEqual(result["status"], "ok")

        stats = fake_redis.hashes.get(f"mockmate:video_stats:{session.id}")
        self.assertIsNotNone(stats)
        self.assertEqual(stats["total_frames"], "1")

    @patch("interviewapp.services.video_service.get_redis_client")
    def test_two_worker_shared_redis_counter(self, mock_get_redis):
        # Simulate shared central Redis instance accessed across worker processes
        shared_redis = MockRedisClient()
        mock_get_redis.return_value = shared_redis

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Backend Developer",
            total_questions=1,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        # Worker 1 processes 2 frames
        process_video_frame(session.id, dummy_frame, frame_id="w1_f1")
        process_video_frame(session.id, dummy_frame, frame_id="w1_f2")

        # Worker 2 processes 3 frames concurrently
        process_video_frame(session.id, dummy_frame, frame_id="w2_f1")
        process_video_frame(session.id, dummy_frame, frame_id="w2_f2")
        process_video_frame(session.id, dummy_frame, frame_id="w2_f3")

        stats = shared_redis.hashes.get(f"mockmate:video_stats:{session.id}")
        self.assertEqual(stats["total_frames"], "5")

    @patch("interviewapp.services.video_service.get_redis_client")
    def test_concurrent_frame_upload_and_finalization(self, mock_get_redis):
        shared_redis = MockRedisClient()
        mock_get_redis.return_value = shared_redis

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        process_video_frame(session.id, dummy_frame, frame_id="f1")

        # Finalize session
        with patch("interviewapp.services.video_service.generate_video_behavior_feedback") as mock_fb:
            mock_fb.return_value = {"summary": "Great composure", "strengths": [], "improvements": []}
            finalize_session_video_metrics(session)

        # Attempt to upload frame after finalization -> Lua script rejects with SESSION_FINALIZED
        result = process_video_frame(session.id, dummy_frame, frame_id="f2_late")
        self.assertEqual(result["status"], "error")
        self.assertIn("already completed or finalized", result["error"])

    @patch("interviewapp.services.video_service.get_redis_client")
    def test_frame_upload_after_finalization_db(self, mock_get_redis):
        # Redis not configured (Database fallback mode)
        mock_get_redis.return_value = None

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
            completed=True,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        result = process_video_frame(session.id, dummy_frame, frame_id="f_late")
        self.assertEqual(result["status"], "error")
        self.assertEqual(result["error"], "Session is already completed.")

        # Also verify HTTP upload_frame view rejects
        self.client.force_login(self.user)
        dummy_file = SimpleUploadedFile("frame.jpg", b"fake bytes", content_type="image/jpeg")
        resp = self.client.post(
            reverse("interviewapp:upload_frame"),
            {"session_id": session.id, "frame": dummy_file, "frame_id": "f_http_late"}
        )
        self.assertEqual(resp.status_code, 400)
        self.assertIn("already completed", resp.json().get("error", ""))

    @patch("interviewapp.services.video_service.get_redis_client")
    def test_duplicate_frame_uuid(self, mock_get_redis):
        # 1. Test in DB mode
        mock_get_redis.return_value = None
        session_db = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
        )
        dummy_frame = b"\x00\x01\x02\x03"
        r1 = process_video_frame(session_db.id, dummy_frame, frame_id="unique-uuid-1")
        self.assertEqual(r1["status"], "ok")
        session_db.refresh_from_db()
        self.assertEqual(session_db.video_stats_json["total_frames"], 1)

        # Retry identical frame UUID
        r2 = process_video_frame(session_db.id, dummy_frame, frame_id="unique-uuid-1")
        self.assertEqual(r2["status"], "ok")
        session_db.refresh_from_db()
        self.assertEqual(session_db.video_stats_json["total_frames"], 1)

        # 2. Test in Redis mode
        shared_redis = MockRedisClient()
        mock_get_redis.return_value = shared_redis
        session_redis = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
        )
        process_video_frame(session_redis.id, dummy_frame, frame_id="redis-uuid-1")
        process_video_frame(session_redis.id, dummy_frame, frame_id="redis-uuid-1")
        stats = shared_redis.hashes.get(f"mockmate:video_stats:{session_redis.id}")
        self.assertEqual(stats["total_frames"], "1")

    @patch("interviewapp.services.video_service.get_redis_client")
    def test_redis_connection_failure(self, mock_get_redis):
        broken_redis = MagicMock()
        broken_redis.eval.side_effect = RuntimeError("Redis connection timeout")
        mock_get_redis.return_value = broken_redis

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
        )
        dummy_frame = b"\x00\x01\x02\x03"
        res = process_video_frame(session.id, dummy_frame)
        self.assertEqual(res["status"], "error")
        self.assertIn("Redis communication error", res["error"])

    @patch("interviewapp.services.video_service.get_redis_client")
    def test_redis_persistence_recovery(self, mock_get_redis):
        shared_redis = MockRedisClient()
        mock_get_redis.return_value = shared_redis

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="AI Engineer",
            total_questions=1,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        process_video_frame(session.id, dummy_frame, frame_id="rec_1")
        process_video_frame(session.id, dummy_frame, frame_id="rec_2")

        # Simulate process crash right after Redis marked finalized but before DB save
        shared_redis.hashes[f"mockmate:video_stats:{session.id}"]["finalized"] = "1"

        with patch("interviewapp.services.video_service.generate_video_behavior_feedback") as mock_fb:
            mock_fb.return_value = {"summary": "Composed", "strengths": [], "improvements": []}
            summary, feedback = finalize_session_video_metrics(session)

        session.refresh_from_db()
        self.assertIsNotNone(session.video_stats_json)
        self.assertEqual(session.video_stats_json["total_frames"], 2)

    @patch("interviewapp.services.video_service.get_redis_client")
    @patch("interviewapp.models.InterviewSession.objects.select_for_update")
    def test_sqlite_retry_exhaustion(self, mock_select, mock_get_redis):
        mock_get_redis.return_value = None
        mock_select.side_effect = OperationalError("database is locked")

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="DevOps",
            total_questions=1,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        res = process_video_frame(session.id, dummy_frame)
        self.assertEqual(res["status"], "error")
        self.assertIn("Database busy", res["error"])

    def test_repeated_finalization_without_repeated_groq_calls(self):
        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
            completed=True,
            video_stats_json={
                "total_frames": 50,
                "face_present_frames": 48,
                "multiple_faces_frames": 0,
                "eye_contact_frames": 45,
                "head_movement_frames": 10,
            },
            video_feedback_json={"summary": "Pre-computed AI feedback", "strengths": ["Eye contact"]},
        )

        with patch("interviewapp.services.video_service.generate_video_behavior_feedback") as mock_fb:
            summary1, feedback1 = finalize_session_video_metrics(session)
            summary2, feedback2 = finalize_session_video_metrics(session)
            # Must NOT call Groq feedback generator
            mock_fb.assert_not_called()
            self.assertEqual(feedback1["summary"], "Pre-computed AI feedback")
            self.assertEqual(feedback2["summary"], "Pre-computed AI feedback")

    @patch("interviewapp.services.video_service.get_redis_client")
    def test_cleanup_and_ttl_behavior(self, mock_get_redis):
        shared_redis = MockRedisClient()
        mock_get_redis.return_value = shared_redis

        session = InterviewSession.objects.create(
            user=self.user,
            role="tech",
            job_role="Engineer",
            total_questions=1,
        )

        dummy_frame = b"\x00\x01\x02\x03"
        process_video_frame(session.id, dummy_frame, frame_id="ttl_frame")

        stats_key = f"mockmate:video_stats:{session.id}"
        frames_key = f"mockmate:video_frames:{session.id}"

        # Verify 24h TTL was registered
        self.assertEqual(shared_redis.ttls.get(stats_key), 86400)
        self.assertEqual(shared_redis.ttls.get(frames_key), 86400)

        with patch("interviewapp.services.video_service.generate_video_behavior_feedback") as mock_fb:
            mock_fb.return_value = {"summary": "OK", "strengths": [], "improvements": []}
            finalize_session_video_metrics(session)

        # Verify frames key was deleted
        self.assertIn(frames_key, shared_redis.deleted_keys)

