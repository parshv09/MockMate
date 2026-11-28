"""
Serializers for the Dynamic Learning Roadmap REST APIs.
"""

from rest_framework import serializers

from ...models import LearningRoadmap


class LearningRoadmapGenerateSerializer(serializers.Serializer):
    """Validates POST /api/v1/sessions/<pk>/learning-roadmap/ requests."""

    regenerate = serializers.BooleanField(default=False, required=False)


class LearningRoadmapSerializer(serializers.ModelSerializer):
    """Serializes persisted LearningRoadmap skill gaps and structured roadmap JSON."""

    session_id = serializers.IntegerField(source="session.id", read_only=True)

    class Meta:
        model = LearningRoadmap
        fields = [
            "id",
            "session_id",
            "skill_gaps_json",
            "roadmap_json",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

