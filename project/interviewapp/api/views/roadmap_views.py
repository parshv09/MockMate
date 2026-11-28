"""
API views for the session-based Dynamic Learning Roadmap.
"""

import logging

from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from ...models import InterviewSession
from ...services.roadmap_service import (
    RoadmapGenerationInProgressError,
    RoadmapSessionIncompleteError,
    generate_learning_roadmap_for_session,
    get_learning_roadmap,
)
from ..permissions import IsOwner
from ..serializers.roadmap_serializers import (
    LearningRoadmapGenerateSerializer,
    LearningRoadmapSerializer,
)

logger = logging.getLogger(__name__)


class SessionLearningRoadmapAPIView(APIView):
    """
    GET /api/v1/sessions/<pk>/learning-roadmap/
      Returns the saved LearningRoadmap for a completed session, or 404 if not yet generated.

    POST /api/v1/sessions/<pk>/learning-roadmap/
      Generates (or returns cached) LearningRoadmap for a completed session.
      Pass {"regenerate": true} to explicitly regenerate.
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
                {"detail": "Learning roadmap is only available after interview completion."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        roadmap = get_learning_roadmap(session)
        if roadmap is None:
            return Response(
                {"detail": "Learning roadmap has not been generated for this session yet."},
                status=status.HTTP_404_NOT_FOUND,
            )

        serializer = LearningRoadmapSerializer(roadmap, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        session = self.get_object(request, pk)
        serializer = LearningRoadmapGenerateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        force_regenerate = bool(serializer.validated_data.get("regenerate", False))

        try:
            roadmap, created = generate_learning_roadmap_for_session(
                session=session,
                force_regenerate=force_regenerate,
            )
        except RoadmapSessionIncompleteError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except RoadmapGenerationInProgressError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        except Exception as exc:
            logger.exception("Failed to generate learning roadmap for session #%s: %s", session.id, exc)
            return Response(
                {"detail": "Failed to generate learning roadmap. Please try again later."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        out_data = LearningRoadmapSerializer(roadmap, context={"request": request}).data
        return Response(
            out_data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

