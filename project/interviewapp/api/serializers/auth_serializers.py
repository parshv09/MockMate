"""
Authentication and user profile serializers for MockMate REST APIs.
"""

from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from ...models import UserProfile

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """
    Public representation of the authenticated user.
    Never exposes password hashes or sensitive internal fields.
    """

    user_type = serializers.SerializerMethodField()
    target_role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "user_type",
            "target_role",
            "date_joined",
        ]
        read_only_fields = fields

    def get_user_type(self, obj):
        profile = getattr(obj, "profile", None)
        return getattr(profile, "user_type", "student") if profile else "student"

    def get_target_role(self, obj):
        profile = getattr(obj, "profile", None)
        return getattr(profile, "target_role", "") if profile else ""


class RegisterSerializer(serializers.Serializer):
    """
    Validates user registration matching the existing application rules.
    Creates User and UserProfile, then returns JWT credentials.
    """

    first_name = serializers.CharField(max_length=150, required=True, trim_whitespace=True)
    last_name = serializers.CharField(max_length=150, required=True, trim_whitespace=True)
    username = serializers.CharField(max_length=150, min_length=3, required=True, trim_whitespace=True)
    email = serializers.EmailField(required=True, trim_whitespace=True)
    password = serializers.CharField(min_length=8, write_only=True, required=True)
    confirm_password = serializers.CharField(min_length=8, write_only=True, required=True)
    user_type = serializers.ChoiceField(
        choices=[("student", "Student"), ("job_seeker", "Job Seeker")],
        default="student",
        required=False,
    )
    target_role = serializers.CharField(max_length=100, required=False, allow_blank=True, default="")

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("This username is already taken.")
        return value

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("This email is already registered.")
        return value

    def validate_password(self, value):
        if not any(c.isupper() for c in value):
            raise serializers.ValidationError("Password must contain at least one uppercase letter.")
        if not any(c.islower() for c in value):
            raise serializers.ValidationError("Password must contain at least one lowercase letter.")
        if not any(c.isdigit() for c in value):
            raise serializers.ValidationError("Password must contain at least one number.")
        return value

    def validate(self, attrs):
        if attrs.get("password") != attrs.get("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop("confirm_password", None)
        user_type = validated_data.pop("user_type", "student")
        target_role = validated_data.pop("target_role", "")

        user = User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=validated_data["first_name"],
            last_name=validated_data["last_name"],
        )

        profile, created = UserProfile.objects.get_or_create(
            user=user,
            defaults={
                "user_type": user_type,
                "target_role": target_role,
            },
        )
        if not created:
            profile.user_type = user_type
            profile.target_role = target_role
            profile.save(update_fields=["user_type", "target_role", "updated_at"])

        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }


class LoginSerializer(serializers.Serializer):
    """
    Authenticates existing users via username (or email) and password,
    returning a JWT token pair on success.
    """

    username = serializers.CharField(required=True, trim_whitespace=True)
    password = serializers.CharField(required=True, write_only=True)

    def validate(self, attrs):
        username = attrs.get("username", "")
        password = attrs.get("password", "")

        user = authenticate(username=username, password=password)

        # Allow login via email if username didn't match directly
        if user is None and "@" in username:
            user_by_email = User.objects.filter(email__iexact=username).first()
            if user_by_email:
                user = authenticate(username=user_by_email.username, password=password)

        if not user:
            raise serializers.ValidationError("Invalid credentials.")

        if not user.is_active:
            raise serializers.ValidationError("This user account is disabled.")

        refresh = RefreshToken.for_user(user)
        return {
            "user": user,
            "tokens": {
                "access": str(refresh.access_token),
                "refresh": str(refresh),
            },
        }

