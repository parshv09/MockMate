import logging
import requests

from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
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


class SessionAvatarTokenAPIView(APIView):
    """
    POST /api/v1/sessions/<pk>/avatar/token/
    Exchanges server-side LIVEAVATAR_API_KEY for a short-lived, single-use
    HeyGen LiveAvatar WebRTC session token without exposing API keys to the client.
    """

    permission_classes = [IsAuthenticated, IsOwner]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def post(self, request, pk: int):
        session = _get_owned_session(request, pk)
        self.check_object_permissions(request, session)

        if session.completed:
            return Response(
                {"detail": "Cannot create a live avatar token for a completed interview session."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        api_key = (getattr(settings, "LIVEAVATAR_API_KEY", "") or "").strip()
        avatar_id = (getattr(settings, "LIVEAVATAR_AVATAR_ID", "") or "").strip()
        token_url = (
            getattr(settings, "LIVEAVATAR_TOKEN_URL", "https://api.liveavatar.com/v1/sessions/token")
            or "https://api.liveavatar.com/v1/sessions/token"
        ).strip()

        if not api_key or not avatar_id:
            return Response(
                {
                    "detail": "LiveAvatar credentials (LIVEAVATAR_API_KEY and LIVEAVATAR_AVATAR_ID) are not configured on the server.",
                },
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        persona = {"language": "en"}
        voice_id = (getattr(settings, "LIVEAVATAR_VOICE_ID", "") or "").strip()
        context_id = (getattr(settings, "LIVEAVATAR_CONTEXT_ID", "") or "").strip()
        if voice_id:
            persona["voice_id"] = voice_id
        if context_id:
            persona["context_id"] = context_id

        payload = {
            "mode": "FULL",
            "avatar_id": avatar_id,
            "avatar_persona": persona,
        }

        try:
            upstream_resp = requests.post(
                token_url,
                headers={
                    "X-API-KEY": api_key,
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
                json=payload,
                timeout=15,
            )
        except requests.RequestException as exc:
            logger.error("LiveAvatar token exchange request failed for session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Unable to reach the LiveAvatar token service. Please try again later."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            body = upstream_resp.json() if upstream_resp.content else {}
        except ValueError:
            body = {}

        nested_data = body.get("data") if isinstance(body, dict) and isinstance(body.get("data"), dict) else {}
        session_token = (
            nested_data.get("session_token")
            or (body.get("session_token") if isinstance(body, dict) else None)
            or (body.get("token") if isinstance(body, dict) else None)
        )

        if not upstream_resp.ok or not session_token:
            logger.warning(
                "LiveAvatar token exchange rejected for session #%s (HTTP %s): %s",
                session.id,
                upstream_resp.status_code,
                body.get("message") if isinstance(body, dict) else "No token returned",
            )
            return Response(
                {"detail": "Failed to obtain a valid session token from LiveAvatar."},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "session_token": session_token,
                "avatar_session_id": nested_data.get("session_id"),
                "provider": "heygen_liveavatar",
            },
            status=status.HTTP_200_OK,
        )


