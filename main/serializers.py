from django.utils.html import strip_tags
from rest_framework import serializers

from main.models import Project


class ProjectSerializer(serializers.ModelSerializer):
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

    def validate_title(self, value):
        value = strip_tags(value).strip()
        if not value:
            raise serializers.ValidationError("Title cannot be empty.")
        return value

    def validate_description(self, value):
        return strip_tags(value)

    def validate_tech_stack(self, value):
        return strip_tags(value)

    def get_star_count(self, obj):
        return obj.starred_by.count()

    def get_is_starred(self, obj):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return False
        return request.user in obj.starred_by.all()

    def get_starred_by_names(self, obj):
        return ", ".join(user.username for user in obj.starred_by.all())

    def create(self, validated_data):
        tech = validated_data.pop("tech_stack", None)
        if tech and not validated_data.get("category"):
            validated_data["category"] = tech
        return super().create(validated_data)

    def update(self, instance, validated_data):
        tech = validated_data.pop("tech_stack", None)
        if tech and not validated_data.get("category"):
            validated_data["category"] = tech
        return super().update(instance, validated_data)

    def to_representation(self, instance):
        ret = super().to_representation(instance)
        if not ret.get("tech_stack"):
            tags_str = ", ".join(tag.name for tag in instance.tags.all())
            ret["tech_stack"] = tags_str or instance.category or "General"
        return ret
