"""
Resume serializers for MockMate REST APIs.
"""

import os
from rest_framework import serializers

from ...models import Resume
from ...services.resume_service import (
    ALLOWED_RESUME_EXTENSIONS,
    MAX_RESUME_FILE_SIZE_BYTES,
    save_and_index_resume,
    validate_resume_file,
)

ALLOWED_EXTENSIONS = ALLOWED_RESUME_EXTENSIONS
MAX_FILE_SIZE_BYTES = MAX_RESUME_FILE_SIZE_BYTES


class ResumeListSerializer(serializers.ModelSerializer):
    """
    List view representation of a candidate's saved resume.
    Excludes internal file system paths and private RAG vector data.
    """

    file_name = serializers.SerializerMethodField()
    file_url = serializers.SerializerMethodField()
    has_file = serializers.SerializerMethodField()

    class Meta:
        model = Resume
        fields = [
            "id",
            "title",
            "file_name",
            "file_url",
            "has_file",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_file_name(self, obj):
        if obj.original_file:
            return os.path.basename(obj.original_file.name)
        return None

    def get_file_url(self, obj):
        if obj.original_file:
            request = self.context.get("request")
            url = obj.original_file.url
            if request is not None:
                return request.build_absolute_uri(url)
            return url
        return None

    def get_has_file(self, obj):
        return bool(obj.original_file)


class ResumeDetailSerializer(ResumeListSerializer):
    """
    Detailed metadata representation of a single resume.
    Includes text excerpt length without leaking sensitive vector embeddings.
    """

    text_length = serializers.SerializerMethodField()

    class Meta(ResumeListSerializer.Meta):
        fields = ResumeListSerializer.Meta.fields + ["text_length"]

    def get_text_length(self, obj):
        return len(obj.extracted_text or "")


class ResumeUploadSerializer(serializers.Serializer):
    """
    Validates resume upload (multipart form-data or raw text) and triggers
    ChromaDB vector indexing via save_and_index_resume.
    """

    title = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    file = serializers.FileField(required=False, allow_null=True)
    raw_text = serializers.CharField(required=False, allow_blank=True, default="")

    def validate_file(self, value):
        if value:
            try:
                validate_resume_file(value)
            except ValueError as exc:
                raise serializers.ValidationError(str(exc))
        return value

    def validate(self, attrs):
        file_obj = attrs.get("file")
        raw_text = attrs.get("raw_text", "").strip()

        if not file_obj and not raw_text:
            raise serializers.ValidationError("Please provide either a resume file or pasted resume text.")
        return attrs

    def create(self, validated_data):
        user = self.context["request"].user
        title = validated_data.get("title", "").strip()
        file_obj = validated_data.get("file")
        raw_text = validated_data.get("raw_text", "").strip()

        resume_obj = save_and_index_resume(
            user=user,
            title=title,
            file_obj=file_obj,
            raw_text=raw_text,
        )

        if not resume_obj:
            raise serializers.ValidationError(
                "Could not extract meaningful content from the provided resume. Please verify the file or text."
            )
        return resume_obj

