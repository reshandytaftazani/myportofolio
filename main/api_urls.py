"""API routing configuration for portfolio DRF endpoints."""

from django.urls import path

from main import api_views

app_name = "api"

urlpatterns = [
    # Projects Endpoints (Tutorial 07)
    path("projects/", api_views.project_list, name="project-list"),
    path("projects/<uuid:project_id>/", api_views.project_detail, name="project-detail"),
    path("projects/<uuid:project_id>/star/", api_views.project_star, name="project-star"),

    # Experiences Endpoints (Tugas 6)
    path("experiences/", api_views.experience_list, name="experience-list"),
    path("experiences/<uuid:experience_id>/", api_views.experience_detail, name="experience-detail"),
    path("experiences/<uuid:experience_id>/star/", api_views.experience_star, name="experience-star"),

    # Skills Endpoints (Sub-tahap 6.2 Skor 4.0)
    path("skills/", api_views.skill_list, name="skill-list"),
    path("skills/<uuid:skill_id>/", api_views.skill_detail, name="skill-detail"),
    path("skills/<uuid:skill_id>/star/", api_views.skill_star, name="skill-star"),

    # Education Endpoints (Sub-tahap 6.3 Skor 4.0)
    path("education/", api_views.education_list, name="education-list"),
    path("education/<int:education_id>/", api_views.education_detail, name="education-detail"),
    path("education/<int:education_id>/star/", api_views.education_star, name="education-star"),
]
