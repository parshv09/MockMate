import io
import os
from PIL import Image, UnidentifiedImageError
from rest_framework import serializers


MAX_VIDEO_FRAME_BYTES = 5 * 1024 * 1024  # 5 MB
ALLOWED_FRAME_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_FRAME_CONTENT_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
}


class VideoFrameUploadSerializer(serializers.Serializer):
    """Validates uploaded video frame payloads before OpenCV/MediaPipe analysis."""

    frame = serializers.FileField(required=True)
    frame_id = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=128,
    )

    def validate_frame(self, value):
        size = getattr(value, "size", None)
        if size is None or size <= 0:
            raise serializers.ValidationError("Uploaded frame file is empty.")

        if size > MAX_VIDEO_FRAME_BYTES:
            raise serializers.ValidationError(
                f"Uploaded frame exceeds the maximum allowed size of {MAX_VIDEO_FRAME_BYTES // (1024 * 1024)} MB."
            )

        filename = getattr(value, "name", "") or ""
        ext = os.path.splitext(filename)[1].lower()
        if ext and ext not in ALLOWED_FRAME_EXTENSIONS:
            raise serializers.ValidationError(
                "Unsupported image file extension. Allowed formats: JPEG, PNG, WEBP."
            )

        content_type = (getattr(value, "content_type", "") or "").lower().strip()
        if content_type and content_type != "application/octet-stream":
            if content_type not in ALLOWED_FRAME_CONTENT_TYPES:
                raise serializers.ValidationError(
                    "Unsupported image content type. Allowed formats: image/jpeg, image/png, image/webp."
                )

        # Verify actual image bytes using Pillow so corrupt payloads fail cleanly with 400.
        try:
            value.seek(0)
            raw_bytes = value.read()
            if not raw_bytes:
                raise serializers.ValidationError("Uploaded frame file is empty.")
            with Image.open(io.BytesIO(raw_bytes)) as img:
                img.verify()
        except serializers.ValidationError:
            raise
        except (UnidentifiedImageError, OSError, ValueError):
            raise serializers.ValidationError("Uploaded file is not a valid image.")
        finally:
            try:
                value.seek(0)
            except Exception:
                pass

        return value

    def validate_frame_id(self, value):
        cleaned = (value or "").strip()
        return cleaned or None

