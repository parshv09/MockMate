import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import InterviewSession
from ...services.video_service import (
    VideoServiceUnavailableError,
    finalize_session_video_metrics,
    get_session_video_metrics,
    process_video_frame,
)
from ..permissions import IsOwner
from ..serializers.video_serializers import VideoFrameUploadSerializer

logger = logging.getLogger(__name__)


def _get_owned_session(request, pk: int) -> InterviewSession:
    """Fetch an InterviewSession scoped to the authenticated user and enforce IsOwner."""
    session = get_object_or_404(InterviewSession, pk=pk, user=request.user)
    return session


class SessionVideoFrameAPIView(APIView):
    """
    POST /api/v1/sessions/<pk>/video/frame/
    Accepts a validated image frame (and optional frame_id) for real-time behavioral analysis.
    """

    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, pk: int):
        session = _get_owned_session(request, pk)
        self.check_object_permissions(request, session)

        if session.completed or (session.video_stats_json or {}).get("_finalized"):
            return Response(
                {
                    "status": "error",
                    "detail": "Video processing is closed because the session is already completed or finalized.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = VideoFrameUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        frame_file = serializer.validated_data["frame"]
        frame_id = serializer.validated_data.get("frame_id")

        try:
            frame_file.seek(0)
            image_bytes = frame_file.read()
        except Exception:
            logger.exception("Failed reading uploaded video frame for session %s", session.id)
            return Response(
                {"status": "error", "detail": "Unable to read uploaded frame payload."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            result = process_video_frame(session.id, image_bytes, frame_id=frame_id)
        except Exception:
            logger.exception("Unexpected error processing video frame for session %s", session.id)
            return Response(
                {
                    "status": "error",
                    "detail": "Video analysis service is temporarily unavailable.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if result.get("status") == "error":
            if result.get("error_code") == "service_unavailable":
                return Response(
                    {
                        "status": "error",
                        "detail": "Video storage service is temporarily unavailable.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )
            return Response(
                {
                    "status": "error",
                    "detail": result.get("error") or "Failed to process video frame.",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(
            {
                "status": "ok",
                "session_id": session.id,
                "faces": result.get("faces", 0),
                "eye_contact": bool(result.get("eye_contact", False)),
                "head_movement": bool(result.get("head_movement", False)),
            },
            status=status.HTTP_200_OK,
        )


class SessionVideoMetricsAPIView(APIView):
    """
    GET /api/v1/sessions/<pk>/video/metrics/
    Returns sanitized video metrics, summary, and AI feedback (if finalized) for the session.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get(self, request, pk: int):
        session = _get_owned_session(request, pk)
        self.check_object_permissions(request, session)

        try:
            metrics = get_session_video_metrics(session)
        except VideoServiceUnavailableError:
            return Response(
                {
                    "status": "error",
                    "detail": "Video metrics service is temporarily unavailable.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Failed retrieving video metrics for session %s", session.id)
            return Response(
                {
                    "status": "error",
                    "detail": "Unable to retrieve video metrics at this time.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        return Response(metrics, status=status.HTTP_200_OK)


class SessionVideoFinalizeAPIView(APIView):
    """
    POST /api/v1/sessions/<pk>/video/finalize/
    Idempotently finalizes video metrics, computes confidence summary, and generates AI feedback.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def post(self, request, pk: int):
        session = _get_owned_session(request, pk)
        self.check_object_permissions(request, session)

        try:
            video_summary, video_feedback = finalize_session_video_metrics(session)
        except VideoServiceUnavailableError:
            return Response(
                {
                    "status": "error",
                    "detail": "Video finalization service is temporarily unavailable.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        except Exception:
            logger.exception("Failed finalizing video metrics for session %s", session.id)
            return Response(
                {
                    "status": "error",
                    "detail": "Unable to finalize video metrics at this time.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        session.refresh_from_db()
        return Response(
            {
                "status": "ok",
                "session_id": session.id,
                "is_finalized": bool(
                    session.completed or (session.video_stats_json or {}).get("_finalized")
                ),
                "video_summary": video_summary,
                "video_ai_feedback": video_feedback,
            },
            status=status.HTTP_200_OK,
        )

