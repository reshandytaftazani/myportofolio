"""Serializers for Portfolio REST API models."""

from typing import Any, Optional
from django.utils.html import strip_tags
from rest_framework import serializers

from urllib.parse import urlsplit
from main.models import Education, Experience, Project, Skill, TechStack


class ProjectSerializer(serializers.ModelSerializer):
    """Serializer for Project model supporting tags, computed stars, and HTML sanitization."""

    star_count = serializers.SerializerMethodField()
    is_starred = serializers.SerializerMethodField()
    starred_by_names = serializers.SerializerMethodField()
    tech_stack = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = Project
        fields = [
            "id",
            "title",
            "description",
            "category",
            "tech_stack",
            "project_url",
            "project_image_url",
            "is_featured",
            "star_count",
            "is_starred",
            "starred_by_names",
        ]
        read_only_fields = ["id"]

    def validate_title(self, value: str) -> str:
        """Sanitize and validate project title."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_description(self, value: str) -> str:
        """Sanitize project description by stripping HTML tags."""
        return strip_tags(value)

    def validate_tech_stack(self, value: str) -> str:
        """Sanitize tech stack string."""
        return strip_tags(value)

    def get_star_count(self, obj: Project) -> int:
        """Return total number of users who starred this project."""
        return obj.starred_by.count()

    def get_is_starred(self, obj: Project) -> bool:
        """Determine whether current authenticated user has starred this project."""
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return request.user in obj.starred_by.all()

    def get_starred_by_names(self, obj: Project) -> str:
        """Return comma-separated usernames who starred this project without exposing sensitive data."""
        return ", ".join(user.username for user in obj.starred_by.all())

    def create(self, validated_data: dict[str, Any]) -> Project:
        """Create a new project instance, mapping tech_stack to category if needed."""
        tech = validated_data.pop("tech_stack", None)
        if tech and not validated_data.get("category"):
            validated_data["category"] = tech
        return super().create(validated_data)

    def update(self, instance: Project, validated_data: dict[str, Any]) -> Project:
        """Update an existing project instance, mapping tech_stack to category if needed."""
        tech = validated_data.pop("tech_stack", None)
        if tech and not validated_data.get("category"):
            validated_data["category"] = tech
        return super().update(instance, validated_data)

    def to_representation(self, instance: Project) -> dict[str, Any]:
        """Format serialized dictionary, ensuring tech_stack is populated from tags or category."""
        ret = super().to_representation(instance)
        if not ret.get("tech_stack"):
            tags_str = ", ".join(tag.name for tag in instance.tags.all())
            ret["tech_stack"] = tags_str or instance.category or "General"
        return ret


class ExperienceSerializer(serializers.ModelSerializer):
    """Serializer for Experience model with explicit fields, RBAC safety, and date validation."""

    star_count = serializers.SerializerMethodField()
    is_starred = serializers.SerializerMethodField()
    starred_by_names = serializers.SerializerMethodField()
    is_ongoing = serializers.BooleanField(read_only=True)
    category_display = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = Experience
        fields = [
            "id",
            "title",
            "company",
            "description",
            "category",
            "category_display",
            "thumbnail",
            "started_at",
            "ended_at",
            "is_ongoing",
            "star_count",
            "is_starred",
            "starred_by_names",
        ]
        read_only_fields = ["id", "is_ongoing", "category_display"]

    def validate_title(self, value: str) -> str:
        """Sanitize and validate that experience title is not empty after stripping HTML."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_company(self, value: Optional[str]) -> Optional[str]:
        """Sanitize company name by stripping HTML tags."""
        if value:
            return strip_tags(value).strip()
        return value

    def validate_description(self, value: str) -> str:
        """Sanitize description by stripping HTML tags."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Description cannot be empty.")
        return value

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        """Validate relational date logic: ended_at must be >= started_at."""
        started_at = (
            attrs.get("started_at")
            if "started_at" in attrs
            else getattr(self.instance, "started_at", None)
        )
        ended_at = (
            attrs.get("ended_at")
            if "ended_at" in attrs
            else getattr(self.instance, "ended_at", None)
        )

        if started_at and ended_at and ended_at < started_at:
            raise serializers.ValidationError(
                {"ended_at": "Ended date cannot be earlier than started date."}
            )
        return attrs

    def get_star_count(self, obj: Experience) -> int:
        """Return total number of users who starred this experience."""
        return obj.starred_by.count()

    def get_is_starred(self, obj: Experience) -> bool:
        """Determine whether current authenticated user has starred this experience."""
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return request.user in obj.starred_by.all()

    def get_starred_by_names(self, obj: Experience) -> str:
        """Return comma-separated usernames who starred this experience without exposing sensitive data."""
        return ", ".join(user.username for user in obj.starred_by.all())


class SkillSerializer(serializers.ModelSerializer):
    """Serializer for Skill model with computed stars, RBAC safety, and HTML sanitization."""

    star_count = serializers.SerializerMethodField()
    is_starred = serializers.SerializerMethodField()
    starred_by_names = serializers.SerializerMethodField()

    class Meta:
        model = Skill
        fields = [
            "id",
            "title",
            "description",
            "level",
            "code_snippet",
            "star_count",
            "is_starred",
            "starred_by_names",
        ]
        read_only_fields = ["id"]

    def validate_title(self, value: str) -> str:
        """Sanitize and validate that skill title is not empty after stripping HTML."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_description(self, value: str) -> str:
        """Sanitize description by stripping HTML tags."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Description cannot be empty.")
        return value

    def validate_level(self, value: str) -> str:
        """Sanitize level by stripping HTML tags."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Level cannot be empty.")
        return value

    def validate_code_snippet(self, value: Optional[str]) -> Optional[str]:
        """Strip extra surrounding whitespaces from code snippet."""
        if value:
            return value.strip()
        return value

    def get_star_count(self, obj: Skill) -> int:
        """Return total number of users who starred this skill."""
        return obj.starred_by.count()

    def get_is_starred(self, obj: Skill) -> bool:
        """Determine whether current authenticated user has starred this skill."""
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return request.user in obj.starred_by.all()

    def get_starred_by_names(self, obj: Skill) -> str:
        """Return comma-separated usernames who starred this skill without exposing sensitive data."""
        return ", ".join(user.username for user in obj.starred_by.all())


class EducationSerializer(serializers.ModelSerializer):
    """Serializer for Education model with computed stars, RBAC safety, and HTML sanitization."""

    star_count = serializers.SerializerMethodField()
    is_starred = serializers.SerializerMethodField()
    starred_by_names = serializers.SerializerMethodField()

    class Meta:
        model = Education
        fields = [
            "id",
            "school_name",
            "period",
            "detail",
            "start_year",
            "star_count",
            "is_starred",
            "starred_by_names",
        ]
        read_only_fields = ["id"]

    def validate_school_name(self, value: str) -> str:
        """Sanitize and validate that school name is not empty after stripping HTML."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("School name cannot be empty.")
        return value

    def validate_period(self, value: str) -> str:
        """Sanitize and validate that period is not empty after stripping HTML."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Period cannot be empty.")
        return value

    def validate_detail(self, value: str) -> str:
        """Sanitize and validate that detail is not empty after stripping HTML."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Detail cannot be empty.")
        return value

    def get_star_count(self, obj: Education) -> int:
        """Return total number of users who starred this education record."""
        return obj.starred_by.count()

    def get_is_starred(self, obj: Education) -> bool:
        """Determine whether current authenticated user has starred this education record."""
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return request.user in obj.starred_by.all()

    def get_starred_by_names(self, obj: Education) -> str:
        """Return comma-separated usernames who starred this education record without exposing sensitive data."""
        return ", ".join(user.username for user in obj.starred_by.all())


class TechStackSerializer(serializers.ModelSerializer):
    """Serializer for TechStack model with computed stars, RBAC safety, and input validation."""

    code_snippet = serializers.CharField(
        trim_whitespace=False,
        help_text="Contoh kode program",
    )
    star_count = serializers.SerializerMethodField()
    is_starred = serializers.SerializerMethodField()
    starred_by_names = serializers.SerializerMethodField()

    class Meta:
        model = TechStack
        fields = [
            "id",
            "name",
            "icon_url",
            "filename",
            "code_snippet",
            "order",
            "star_count",
            "is_starred",
            "starred_by_names",
        ]
        read_only_fields = ["id"]

    def validate_name(self, value: str) -> str:
        """Sanitize plain text name and reject if empty after stripping tags."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Name cannot be empty.")
        return value

    def validate_filename(self, value: str) -> str:
        """Sanitize plain text filename and reject if empty after stripping tags."""
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Filename cannot be empty.")
        return value

    def validate_icon_url(self, value: str) -> str:
        """Validate that icon_url uses http or https scheme only."""
        scheme = urlsplit(value).scheme.lower()
        if scheme not in {"http", "https"}:
            raise serializers.ValidationError("Only http and https schemes are permitted for icon_url.")
        return value

    def validate_code_snippet(self, value: str) -> str:
        """Validate code snippet is not empty while preserving raw code content exactly."""
        if not value.strip():
            raise serializers.ValidationError("Code snippet cannot be empty.")
        return value

    def get_star_count(self, obj: TechStack) -> int:
        """Return total number of users who starred this tech stack."""
        return obj.starred_by.count()

    def get_is_starred(self, obj: TechStack) -> bool:
        """Determine whether current authenticated user has starred this tech stack."""
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return request.user in obj.starred_by.all()

    def get_starred_by_names(self, obj: TechStack) -> str:
        """Return comma-separated usernames who starred this tech stack without exposing sensitive data."""
        return ", ".join(user.username for user in obj.starred_by.all())
