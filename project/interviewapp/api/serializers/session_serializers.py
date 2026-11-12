"""
Session serializers for MockMate REST APIs.
"""

import os
from rest_framework import serializers
from rest_framework.exceptions import NotFound

from ...models import Answer, GeneratedQuestion, InterviewSession, Resume
from ...services.resume_service import validate_resume_file

VALID_ROLES = ["tech", "hr", "apt", "beh"]


class SessionListSerializer(serializers.ModelSerializer):
    """
    List view representation of an interview session.
    Hides internal AI prompts, private file paths, and answer keys.
    """

    duration = serializers.IntegerField(read_only=True)
    answered_count = serializers.IntegerField(read_only=True)
    has_resume = serializers.SerializerMethodField()
    has_job_description = serializers.SerializerMethodField()

    class Meta:
        model = InterviewSession
        fields = [
            "id",
            "role",
            "job_role",
            "difficulty",
            "total_questions",
            "answered_count",
            "current_index",
            "state",
            "completed",
            "total_score",
            "duration",
            "started_at",
            "completed_at",
            "has_resume",
            "has_job_description",
        ]
        read_only_fields = fields

    def get_has_resume(self, obj):
        return obj.resume_id is not None

    def get_has_job_description(self, obj):
        return bool(obj.job_description and obj.job_description.strip())


class SessionDetailSerializer(SessionListSerializer):
    """
    Detailed representation of a specific interview session.
    Excludes answer keys, hidden scoring rubrics, and internal vectors.
    """

    resume_id = serializers.IntegerField(source="resume.id", read_only=True, allow_null=True)
    resume_title = serializers.CharField(source="resume.title", read_only=True, allow_null=True)
    is_completed = serializers.BooleanField(read_only=True)

    class Meta(SessionListSerializer.Meta):
        fields = SessionListSerializer.Meta.fields + [
            "resume_id",
            "resume_title",
            "job_description",
            "is_completed",
        ]
        read_only_fields = fields


class StandardSessionCreateSerializer(serializers.Serializer):
    """
    Validates input parameters for creating a standard interview session.
    Enforces validation prior to invoking Groq or RAG question generators.
    """

    role = serializers.ChoiceField(
        choices=[("tech", "Tech"), ("hr", "HR"), ("apt", "Aptitude"), ("beh", "Behavioral")],
        default="tech",
        required=False,
    )
    job_role = serializers.CharField(
        max_length=100,
        required=False,
        default="Software Engineer",
        allow_blank=True,
    )
    difficulty = serializers.IntegerField(
        min_value=1,
        max_value=5,
        default=3,
        required=False,
    )
    n_questions = serializers.IntegerField(
        min_value=1,
        max_value=30,
        default=5,
        required=False,
    )

    def validate_job_role(self, value):
        val = (value or "").strip()
        return val if val else "Software Engineer"


class ResumeJDSessionCreateSerializer(serializers.Serializer):
    """
    Validates input parameters for creating a resume/JD tailored interview session.
    Validates resume ownership, file contents, and ensures minimal required context.
    """

    resume_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    resume_file = serializers.FileField(required=False, allow_null=True, default=None)
    resume_text = serializers.CharField(required=False, allow_blank=True, default="")
    resume_title = serializers.CharField(max_length=150, required=False, allow_blank=True, default="")
    job_description = serializers.CharField(required=False, allow_blank=True, default="")
    difficulty = serializers.IntegerField(min_value=1, max_value=5, default=3, required=False)
    n_questions = serializers.IntegerField(min_value=1, max_value=30, default=5, required=False)

    def validate_resume_file(self, value):
        if value:
            try:
                validate_resume_file(value)
            except ValueError as err:
                raise serializers.ValidationError(str(err))
        return value

    def validate(self, attrs):
        request = self.context.get("request")
        user = getattr(request, "user", None)

        resume_id = attrs.get("resume_id")
        resume_file = attrs.get("resume_file")
        resume_text = (attrs.get("resume_text") or "").strip()
        job_description = (attrs.get("job_description") or "").strip()

        resume_obj = None

        # 1. If an existing resume ID was specified, validate ownership
        if resume_id is not None:
            # Check if resume belongs to authenticated user
            resume_obj = Resume.objects.filter(id=resume_id, user=user).first()
            if not resume_obj:
                # Return 404 to avoid exposing whether the resume exists for another user
                raise NotFound("Resume not found.")
            attrs["resume_obj"] = resume_obj
        else:
            attrs["resume_obj"] = None

        # 2. Ensure at least one form of input context is present
        has_resume_input = bool(resume_obj or resume_file or resume_text)
        has_jd_input = bool(job_description)

        if not has_resume_input and not has_jd_input:
            raise serializers.ValidationError(
                "Please provide either a resume (by ID, file upload, or text) or a job description."
            )

        return attrs


class QuestionPublicSerializer(serializers.ModelSerializer):
    """
    Public representation of a question presented to the candidate.
    Strictly excludes expected_answer (answer key), keywords, Groq signatures, and private RAG metadata.
    """

    class Meta:
        model = GeneratedQuestion
        fields = [
            "id",
            "text",
            "role",
            "difficulty",
        ]
        read_only_fields = fields


ALLOWED_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".ogg", ".webm", ".flac", ".aac"}
MAX_AUDIO_FILE_SIZE_BYTES = 25 * 1024 * 1024  # 25 MB


class AnswerSubmitSerializer(serializers.Serializer):
    """
    Validates candidate answer submission inputs (text and/or audio file).
    Enforces audio container and size constraints.
    """

    answer_id = serializers.IntegerField(required=False, allow_null=True, default=None)
    answer_text = serializers.CharField(required=False, allow_blank=True, default="")
    audio_file = serializers.FileField(required=False, allow_null=True, default=None)

    def validate_audio_file(self, value):
        if value:
            name = getattr(value, "name", "")
            ext = os.path.splitext(name)[1].lower() if name else ""
            if not ext or ext not in ALLOWED_AUDIO_EXTENSIONS:
                allowed_str = ", ".join(sorted(ALLOWED_AUDIO_EXTENSIONS))
                raise serializers.ValidationError(
                    f"Unsupported audio format '{ext}'. Allowed extensions are: {allowed_str}."
                )

            size = getattr(value, "size", None)
            if size is None and hasattr(value, "seek") and hasattr(value, "tell"):
                pos = value.tell()
                value.seek(0, os.SEEK_END)
                size = value.tell()
                value.seek(pos)

            if size is not None and size > MAX_AUDIO_FILE_SIZE_BYTES:
                raise serializers.ValidationError("Audio file size exceeds maximum limit of 25 MB.")

            if hasattr(value, "seek"):
                value.seek(0)
        return value

    def validate(self, attrs):
        answer_text = (attrs.get("answer_text") or "").strip()
        audio_file = attrs.get("audio_file")

        if not answer_text and not audio_file:
            raise serializers.ValidationError(
                "Please provide either answer_text or an audio_file."
            )

        return attrs


class QuestionSkipSerializer(serializers.Serializer):
    """
    Validates question skipping input.
    """

    answer_id = serializers.IntegerField(required=False, allow_null=True, default=None)


class AnswerEvaluatedSerializer(serializers.ModelSerializer):
    """
    Evaluated answer returned to candidate immediately following submission or skipping.
    Excludes answer keys (expected_answer), internal prompt signatures, and RAG private embeddings.
    """

    has_audio = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = [
            "id",
            "index",
            "answer_text",
            "score",
            "feedback",
            "improvement_tips",
            "resume_grounding",
            "processed",
            "has_audio",
        ]
        read_only_fields = fields

    def get_has_audio(self, obj):
        return bool(obj.audio_file and obj.audio_file.name)


class AnswerSummarySerializer(serializers.ModelSerializer):
    """
    Full answer item within the completed session performance summary.
    Includes question details, score, feedback, improvement tips, resume grounding, and model solution.
    """

    question = QuestionPublicSerializer(read_only=True)
    has_audio = serializers.SerializerMethodField()

    class Meta:
        model = Answer
        fields = [
            "id",
            "index",
            "question",
            "answer_text",
            "score",
            "feedback",
            "improvement_tips",
            "resume_grounding",
            "expected_answer",
            "processed",
            "has_audio",
        ]
        read_only_fields = fields

    def get_has_audio(self, obj):
        return bool(obj.audio_file and obj.audio_file.name)


class SessionSummarySerializer(serializers.Serializer):
    """
    Comprehensive performance summary of a session.
    Serializes aggregate scores, completion rate, duration, AI suggestions, resume grounding,
    video metrics, and question-by-question analysis.
    """

    session = SessionDetailSerializer(read_only=True)
    average_score = serializers.FloatField(source="avg", allow_null=True)
    content_quality_score = serializers.FloatField(allow_null=True)
    completion_rate = serializers.IntegerField()
    duration_minutes = serializers.IntegerField(source="duration")
    strengths = serializers.ListField(child=serializers.CharField(), default=list)
    improvements = serializers.ListField(child=serializers.CharField(), default=list)
    overall_tip = serializers.CharField(allow_blank=True, default="")
    resources = serializers.ListField(child=serializers.CharField(), default=list)
    resume_summary = serializers.DictField(allow_null=True, required=False)
    video_summary = serializers.DictField(allow_null=True, required=False)
    video_ai_feedback = serializers.DictField(allow_null=True, required=False)
    answers = AnswerSummarySerializer(many=True, read_only=True)

