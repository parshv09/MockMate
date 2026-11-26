"""
Session API views for MockMate REST APIs.
"""

import logging
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import InterviewSession
from ...services.adaptive_service import (
    AdaptiveAnswerNotFoundError,
    AdaptiveNoPendingQuestionError,
    AdaptiveSequentialOrderError,
    create_adaptive_session,
    skip_adaptive_question,
    submit_adaptive_answer,
)
from ...services.answer_service import (
    AnswerAlreadyProcessedError,
    AnswerClaimLostError,
    AnswerCurrentlyProcessingError,
    AnswerDatabaseContentionError,
    end_candidate_session,
    skip_candidate_question,
    submit_candidate_answer,
)
from ...services.report_service import build_session_pdf_report
from ...services.session_service import (
    create_resume_jd_session,
    create_standard_session,
    get_next_unprocessed_answer,
    get_session_summary_data,
)
from ..permissions import IsOwner
from ..serializers.session_serializers import (
    AdaptiveSessionCreateSerializer,
    AnswerEvaluatedSerializer,
    AnswerSubmitSerializer,
    QuestionPublicSerializer,
    QuestionSkipSerializer,
    ResumeJDSessionCreateSerializer,
    SessionDetailSerializer,
    SessionListSerializer,
    SessionSummarySerializer,
    StandardSessionCreateSerializer,
)

logger = logging.getLogger(__name__)


class SessionListCreateAPIView(APIView):
    """
    GET /api/v1/sessions/
      Lists all interview sessions owned by the authenticated candidate.

    POST /api/v1/sessions/
      Creates a new standard role-based mock interview session using create_standard_session().
    """

    permission_classes = [IsAuthenticated]

    def get(self, request):
        sessions = InterviewSession.objects.filter(user=request.user).order_by("-started_at")
        serializer = SessionListSerializer(sessions, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = StandardSessionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data["role"]
        job_role = serializer.validated_data["job_role"]
        difficulty = serializer.validated_data["difficulty"]
        n_questions = serializer.validated_data["n_questions"]

        try:
            session, created_count = create_standard_session(
                user=request.user,
                raw_role=role,
                job_role=job_role,
                difficulty=difficulty,
                n_questions=n_questions,
            )
        except Exception as exc:
            logger.exception("Failed to initialize standard interview session for user %s: %s", request.user.id, exc)
            return Response(
                {"detail": "Failed to initialize interview session. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        detail_data = SessionDetailSerializer(session, context={"request": request}).data
        return Response(
            {
                "message": "Standard interview session created successfully.",
                "created_questions": created_count,
                "session": detail_data,
            },
            status=status.HTTP_201_CREATED,
        )


class SessionResumeJDCreateAPIView(APIView):
    """
    POST /api/v1/sessions/resume-jd/
      Creates an interview session tailored to the candidate's resume and job description.
      Reuses create_resume_jd_session() and enforces resume ownership and upload validation.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def post(self, request):
        serializer = ResumeJDSessionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        vdata = serializer.validated_data
        resume_obj = vdata.get("resume_obj")
        job_description = vdata.get("job_description", "")
        difficulty = vdata.get("difficulty", 3)
        n_questions = vdata.get("n_questions", 5)
        resume_title = vdata.get("resume_title", "")
        resume_file = vdata.get("resume_file")
        pasted_resume = vdata.get("resume_text", "")

        try:
            session, created_count = create_resume_jd_session(
                user=request.user,
                resume_obj=resume_obj,
                job_description=job_description,
                difficulty=difficulty,
                n_questions=n_questions,
                resume_title=resume_title,
                resume_file=resume_file,
                pasted_resume=pasted_resume,
            )
        except Exception as exc:
            logger.exception("Failed to initialize resume-tailored session for user %s: %s", request.user.id, exc)
            return Response(
                {"detail": "Failed to initialize resume-tailored session. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        if not session:
            return Response(
                {"detail": "Could not create session. Please provide a valid resume or job description."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        detail_data = SessionDetailSerializer(session, context={"request": request}).data
        return Response(
            {
                "message": "Resume & JD tailored interview session created successfully.",
                "created_questions": created_count,
                "session": detail_data,
            },
            status=status.HTTP_201_CREATED,
        )


class SessionDetailAPIView(APIView):
    """
    GET /api/v1/sessions/<id>/
      Retrieves detailed metadata, timing, and current progress for a candidate's session.
      Returns 404 if the session belongs to another user.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def get(self, request, pk):
        session = self.get_object(request, pk)
        serializer = SessionDetailSerializer(session, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SessionNextQuestionAPIView(APIView):
    """
    GET /api/v1/sessions/<id>/next-question/
      Resolves and returns the next unprocessed question for the candidate to answer.
      Hides expected answers, scoring rubrics, internal prompts, and answer keys.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def get(self, request, pk):
        session = self.get_object(request, pk)
        next_ans = get_next_unprocessed_answer(session)

        if not next_ans:
            return Response(
                {
                    "has_next_question": False,
                    "session_id": session.id,
                    "current_index": session.current_index,
                    "total_questions": session.total_questions,
                    "is_completed": bool(session.completed or session.is_completed),
                    "message": "No remaining questions in this session.",
                },
                status=status.HTTP_200_OK,
            )

        q_data = QuestionPublicSerializer(next_ans.question).data if next_ans.question else None

        return Response(
            {
                "has_next_question": True,
                "session_id": session.id,
                "current_index": next_ans.index,
                "total_questions": session.total_questions,
                "answer_id": next_ans.id,
                "question": q_data,
            },
            status=status.HTTP_200_OK,
        )


class SessionAnswerSubmitAPIView(APIView):
    """
    POST /api/v1/sessions/<id>/answers/
      Submits candidate text or audio answer for the current or specified question.
      Triggers Whisper transcription if audio is supplied without text.
      Evaluates answer using existing NLP scoring and resume grounding.
      Returns evaluated answer and next question.
    """

    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def get(self, request, pk):
        """Lists all evaluated or allocated answers for this session."""
        session = self.get_object(request, pk)
        answers = session.answers.all().order_by("index")
        serializer = AnswerEvaluatedSerializer(answers, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        session = self.get_object(request, pk)

        if session.completed:
            return Response(
                {"detail": "This interview session has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AnswerSubmitSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        current_unanswered = session.answers.filter(processed=False).order_by("index").first()
        if not current_unanswered:
            return Response(
                {"detail": "No unprocessed questions remaining in this session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_id = serializer.validated_data.get("answer_id")
        if answer_id is not None:
            target_ans = session.answers.filter(id=answer_id).first()
            if not target_ans:
                return Response(
                    {"detail": "Answer not found in this session."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if target_ans.processed:
                return Response(
                    {"detail": "This question has already been answered and processed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if target_ans.id != current_unanswered.id:
                return Response(
                    {"detail": "Questions must be answered in sequential order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_ans = current_unanswered

        answer_text = serializer.validated_data.get("answer_text", "")
        audio_file = serializer.validated_data.get("audio_file")

        try:
            ans, is_completed = submit_candidate_answer(
                session=session,
                answer_id=target_ans.id,
                answer_text=answer_text,
                audio_file=audio_file,
            )
        except AnswerAlreadyProcessedError as err:
            logger.warning(
                "Duplicate answer submission for session #%s, answer #%s: %s",
                session.id,
                target_ans.id,
                err,
            )
            return Response(
                {"detail": "This question has already been answered and processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (AnswerCurrentlyProcessingError, AnswerClaimLostError) as err:
            logger.warning(
                "Concurrent answer contention for session #%s, answer #%s: %s",
                session.id,
                target_ans.id,
                err,
            )
            return Response(
                {"detail": "This answer is currently being processed by another request."},
                status=status.HTTP_409_CONFLICT,
            )
        except AnswerDatabaseContentionError as err:
            logger.warning(
                "Database contention during answer submission for session #%s: %s",
                session.id,
                err,
            )
            return Response(
                {"detail": "The server is temporarily busy processing your answer. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValueError as val_err:
            logger.warning("Answer submission validation failed for session #%s: %s", session.id, val_err)
            return Response(
                {"detail": "This question has already been answered and processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Answer submission failed for session #%s, answer #%s: %s", session.id, target_ans.id, exc)
            return Response(
                {"detail": "Failed to process answer submission. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        next_q_data = None
        if not is_completed:
            next_ans = get_next_unprocessed_answer(session)
            if next_ans and next_ans.question:
                next_q_data = QuestionPublicSerializer(next_ans.question).data

        return Response(
            {
                "message": "Answer submitted and evaluated successfully.",
                "is_session_completed": is_completed,
                "answer": AnswerEvaluatedSerializer(ans).data,
                "next_question": next_q_data,
            },
            status=status.HTTP_200_OK,
        )


class SessionQuestionSkipAPIView(APIView):
    """
    POST /api/v1/sessions/<id>/skip/
      Skips the current or specified question (scores 0, processed=True).
      Returns skipped answer and next question.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def post(self, request, pk):
        session = self.get_object(request, pk)

        if session.completed:
            return Response(
                {"detail": "This interview session has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = QuestionSkipSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        current_unanswered = session.answers.filter(processed=False).order_by("index").first()
        if not current_unanswered:
            return Response(
                {"detail": "No unprocessed questions remaining to skip."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_id = serializer.validated_data.get("answer_id")
        if answer_id is not None:
            target_ans = session.answers.filter(id=answer_id).first()
            if not target_ans:
                return Response(
                    {"detail": "Answer not found in this session."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if target_ans.processed:
                return Response(
                    {"detail": "This question has already been answered or skipped."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if target_ans.id != current_unanswered.id:
                return Response(
                    {"detail": "Questions must be answered in sequential order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            target_ans = current_unanswered

        try:
            ans, is_completed = skip_candidate_question(session, answer_id=target_ans.id)
        except AnswerAlreadyProcessedError as err:
            logger.warning(
                "Duplicate question skip for session #%s, answer #%s: %s",
                session.id,
                target_ans.id,
                err,
            )
            return Response(
                {"detail": "This question has already been answered or skipped."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except AnswerCurrentlyProcessingError as err:
            logger.warning(
                "Skip rejected due to active processing for session #%s, answer #%s: %s",
                session.id,
                target_ans.id,
                err,
            )
            return Response(
                {"detail": "This question is currently being processed and cannot be skipped."},
                status=status.HTTP_409_CONFLICT,
            )
        except AnswerDatabaseContentionError as err:
            logger.warning(
                "Database contention during question skip for session #%s: %s",
                session.id,
                err,
            )
            return Response(
                {"detail": "The server is temporarily busy. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except ValueError as val_err:
            logger.warning("Question skip validation failed for session #%s: %s", session.id, val_err)
            return Response(
                {"detail": "This question has already been answered or skipped."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as exc:
            logger.exception("Question skipping failed for session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Failed to skip question. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        next_q_data = None
        if not is_completed:
            next_ans = get_next_unprocessed_answer(session)
            if next_ans and next_ans.question:
                next_q_data = QuestionPublicSerializer(next_ans.question).data

        return Response(
            {
                "message": "Question skipped successfully.",
                "is_session_completed": is_completed,
                "answer": AnswerEvaluatedSerializer(ans).data if ans else None,
                "next_question": next_q_data,
            },
            status=status.HTTP_200_OK,
        )


class SessionEndAPIView(APIView):
    """
    POST /api/v1/sessions/<id>/end/
      Manually ends an active session immediately, marks completion, and flushes video metrics.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def post(self, request, pk):
        session = self.get_object(request, pk)
        try:
            if not session.completed:
                session = end_candidate_session(session)
        except Exception as exc:
            logger.exception("Failed to end interview session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Failed to end interview session. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        detail_data = SessionDetailSerializer(session, context={"request": request}).data
        return Response(
            {
                "message": "Interview session ended successfully.",
                "session": detail_data,
            },
            status=status.HTTP_200_OK,
        )


class SessionSummaryAPIView(APIView):
    """
    GET /api/v1/sessions/<id>/summary/
      Retrieves the complete performance summary, aggregate metrics, AI suggestions,
      resume grounding analysis, video summary, and question-by-question breakdown.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def get(self, request, pk):
        session = self.get_object(request, pk)

        if not session.completed:
            return Response(
                {"detail": "Session performance summary is only available after interview completion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            summary_data = get_session_summary_data(session)
        except Exception as exc:
            logger.exception("Failed to generate summary for session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Failed to retrieve session summary. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        serializer = SessionSummarySerializer(summary_data, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class SessionReportDownloadAPIView(APIView):
    """
    GET /api/v1/sessions/<id>/report/
      Builds and downloads an executive PDF performance report for the session.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def get(self, request, pk):
        session = self.get_object(request, pk)

        if not session.completed:
            return Response(
                {"detail": "Interview report can only be downloaded after session completion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            pdf_buffer = build_session_pdf_report(session)
        except Exception as exc:
            logger.exception("Failed to build PDF report for session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Failed to generate session PDF report. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        response = HttpResponse(pdf_buffer.getvalue(), content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="AI_Interview_Report_{session.id}.pdf"'
        return response


def _build_adaptive_progression_response(result, message: str) -> Response:
    """Formats a consistent response payload for adaptive answer submit & skip endpoints."""
    next_q_data = (
        QuestionPublicSerializer(result.next_answer.question).data
        if (result.next_answer is not None and result.next_answer.question is not None)
        else None
    )
    return Response(
        {
            "message": message,
            "session_id": result.answer.session_id,
            "is_session_completed": result.is_session_completed,
            "answer": AnswerEvaluatedSerializer(result.answer).data,
            "next_question": next_q_data,
            "next_question_kind": result.next_question_kind,
            "main_questions_count": result.main_questions_count,
            "max_main_questions": result.max_main_questions,
            "total_interactions": result.total_interactions,
        },
        status=status.HTTP_200_OK,
    )


class SessionAdaptiveCreateAPIView(APIView):
    """
    POST /api/v1/sessions/adaptive/
      Creates a new Hybrid Adaptive interview session with only the first main question.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = AdaptiveSessionCreateSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        role = serializer.validated_data["role"]
        job_role = serializer.validated_data["job_role"]
        difficulty = serializer.validated_data["difficulty"]
        n_questions = serializer.validated_data["n_questions"]

        try:
            session, created_count = create_adaptive_session(
                user=request.user,
                raw_role=role,
                job_role=job_role,
                difficulty=difficulty,
                max_main_questions=n_questions,
            )
        except ValueError as val_err:
            return Response({"detail": str(val_err)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as exc:
            logger.exception("Failed to initialize adaptive session for user %s: %s", request.user.id, exc)
            return Response(
                {"detail": "Failed to initialize adaptive interview session. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        first_ans = session.answers.select_related("question").order_by("index").first()
        next_q_data = (
            QuestionPublicSerializer(first_ans.question).data
            if (first_ans and first_ans.question)
            else None
        )
        detail_data = SessionDetailSerializer(session, context={"request": request}).data
        return Response(
            {
                "message": "Adaptive interview session created successfully.",
                "created_questions": created_count,
                "session": detail_data,
                "next_question": next_q_data,
                "next_question_kind": "main" if next_q_data else None,
                "main_questions_count": detail_data.get("main_questions_count", 1),
                "max_main_questions": session.max_main_questions,
                "total_interactions": session.total_questions,
            },
            status=status.HTTP_201_CREATED,
        )


class SessionAdaptiveAnswerSubmitAPIView(APIView):
    """
    POST /api/v1/sessions/<id>/adaptive/answers/
      Submits an answer in an adaptive session, evaluates via `submit_candidate_answer(..., auto_complete=False)`,
      runs the adaptive decision engine, and appends a follow-up / next main question or completes.
    """

    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def post(self, request, pk):
        session = self.get_object(request, pk)
        if session.state != "adaptive":
            return Response(
                {"detail": "This endpoint is only available for adaptive interview sessions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = AnswerSubmitSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        answer_id = serializer.validated_data.get("answer_id")
        if session.completed and answer_id is None:
            return Response(
                {"detail": "This interview session has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        answer_text = serializer.validated_data.get("answer_text", "")
        audio_file = serializer.validated_data.get("audio_file")

        try:
            result = submit_adaptive_answer(
                session=session,
                answer_id=answer_id,
                answer_text=answer_text,
                audio_file=audio_file,
            )
        except AnswerAlreadyProcessedError:
            return Response(
                {"detail": "This question has already been answered and processed."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (AdaptiveAnswerNotFoundError, AdaptiveSequentialOrderError, AdaptiveNoPendingQuestionError) as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except (AnswerCurrentlyProcessingError, AnswerClaimLostError):
            return Response(
                {"detail": "This answer is currently being processed by another request."},
                status=status.HTTP_409_CONFLICT,
            )
        except AnswerDatabaseContentionError:
            return Response(
                {"detail": "The server is temporarily busy processing your answer. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Adaptive answer submission failed for session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Failed to process adaptive answer submission. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return _build_adaptive_progression_response(
            result, "Answer submitted and evaluated successfully."
        )


class SessionAdaptiveQuestionSkipAPIView(APIView):
    """
    POST /api/v1/sessions/<id>/adaptive/skip/
      Skips the current question in an adaptive session and advances via the adaptive decision engine.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
        self.check_object_permissions(request, session)
        return session

    def post(self, request, pk):
        session = self.get_object(request, pk)
        if session.state != "adaptive":
            return Response(
                {"detail": "This endpoint is only available for adaptive interview sessions."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = QuestionSkipSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)

        answer_id = serializer.validated_data.get("answer_id")
        if session.completed and answer_id is None:
            return Response(
                {"detail": "This interview session has already been completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = skip_adaptive_question(session=session, answer_id=answer_id)
        except AnswerAlreadyProcessedError:
            return Response(
                {"detail": "This question has already been answered or skipped."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except (AdaptiveAnswerNotFoundError, AdaptiveSequentialOrderError, AdaptiveNoPendingQuestionError) as err:
            return Response({"detail": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except AnswerCurrentlyProcessingError:
            return Response(
                {"detail": "This question is currently being processed and cannot be skipped."},
                status=status.HTTP_409_CONFLICT,
            )
        except AnswerDatabaseContentionError:
            return Response(
                {"detail": "The server is temporarily busy. Please try again."},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception as exc:
            logger.exception("Adaptive question skip failed for session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Failed to skip question. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        return _build_adaptive_progression_response(
            result, "Question skipped successfully."
        )


