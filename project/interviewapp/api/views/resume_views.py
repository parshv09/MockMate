"""
Resume management API views for MockMate REST APIs.
"""

from rest_framework import status
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404

from ...models import Resume
from ...services.resume_service import delete_candidate_resume
from ..permissions import IsOwner
from ..serializers.resume_serializers import (
    ResumeDetailSerializer,
    ResumeListSerializer,
    ResumeUploadSerializer,
)


class ResumeListCreateAPIView(APIView):
    """
    GET /api/v1/resumes/
      Lists all saved resumes owned by the authenticated candidate.

    POST /api/v1/resumes/
      Uploads or pastes a resume, extracts content, indexes vectors in ChromaDB,
      and returns clean metadata (excluding private RAG vector internals).
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get(self, request):
        resumes = Resume.objects.filter(user=request.user).order_by("-created_at")
        serializer = ResumeListSerializer(resumes, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        serializer = ResumeUploadSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        resume_obj = serializer.save()

        detail_serializer = ResumeDetailSerializer(resume_obj, context={"request": request})
        return Response(detail_serializer.data, status=status.HTTP_201_CREATED)


class ResumeDetailAPIView(APIView):
    """
    GET /api/v1/resumes/<id>/
      Retrieves detailed metadata for a candidate's specific resume.

    DELETE /api/v1/resumes/<id>/
      Deletes the saved resume record and its associated physical file.
    """

    permission_classes = [IsAuthenticated, IsOwner]

    def get_object(self, request, pk):
        resume = get_object_or_404(Resume, pk=pk, user=request.user)
        self.check_object_permissions(request, resume)
        return resume

    def get(self, request, pk):
        resume = self.get_object(request, pk)
        serializer = ResumeDetailSerializer(resume, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        resume = self.get_object(request, pk)
        delete_candidate_resume(resume)
        return Response(status=status.HTTP_204_NO_CONTENT)
