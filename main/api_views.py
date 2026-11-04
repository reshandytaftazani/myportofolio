"""Functional API views for portfolio resources using Django REST Framework."""

import uuid
from typing import Any
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from main.models import Experience, Project, Skill
from main.permissions import (
    IsPortfolioOwnerOrReadOnly,
    IsPortfolioOwnerOrEditorOrReadOnly,
)
from main.serializers import (
    ExperienceSerializer,
    ProjectSerializer,
    SkillSerializer,
)


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPortfolioOwnerOrReadOnly])
def project_list(request: Request) -> Response:
    """Retrieve list of projects or create a new project.

    Args:
        request (Request): The incoming REST request.

    Query Params:
        title (str, optional): Filter projects by title (case-insensitive substring).
        category (str, optional): Filter projects by category name.

    Returns:
        Response: List of serialized projects (200 OK) or newly created project (201 Created).

    Error Codes:
        200 OK: Project list successfully retrieved.
        201 Created: New project successfully created.
        400 Bad Request: Invalid input data failed serializer validation.
        403 Forbidden: Unauthenticated or non-superuser attempted POST.
    """
    if request.method in ("GET", "HEAD"):
        projects = Project.objects.prefetch_related("starred_by", "tags").order_by("title", "id")
        title = request.query_params.get("title", "").strip()
        category = request.query_params.get("category", "").strip()
        if title:
            projects = projects.filter(title__icontains=title)
        if category and category.lower() != "all":
            projects = projects.filter(category=category)
        serializer = ProjectSerializer(
            projects, many=True, context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    with transaction.atomic():
        serializer = ProjectSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPortfolioOwnerOrReadOnly])
def project_detail(request: Request, project_id: uuid.UUID) -> Response:
    """Retrieve, update, or delete a specific project.

    Args:
        request (Request): The incoming REST request.
        project_id (uuid.UUID): Primary key of the project.

    Returns:
        Response: Serialized project data (200 OK) or empty body (204 No Content).

    Error Codes:
        200 OK: Project details retrieved or updated successfully.
        204 No Content: Project successfully deleted.
        400 Bad Request: Invalid update payload failed serializer validation.
        403 Forbidden: Unauthenticated or non-superuser attempted mutation.
        404 Not Found: Project with given UUID not found.
    """
    project = get_object_or_404(
        Project.objects.prefetch_related("starred_by", "tags"), pk=project_id,
    )
    if request.method in ("GET", "HEAD"):
        serializer = ProjectSerializer(project, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "DELETE":
        with transaction.atomic():
            project.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    with transaction.atomic():
        serializer = ProjectSerializer(
            project,
            data=request.data,
            partial=request.method == "PATCH",
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def project_star(request: Request, project_id: uuid.UUID) -> Response:
    """Toggle star status on a specific project for the authenticated user.

    Args:
        request (Request): The incoming REST request.
        project_id (uuid.UUID): Primary key of the project.

    Returns:
        Response: Updated serialized project data with refreshed star status (200 OK).

    Error Codes:
        200 OK: Star status successfully toggled.
        403 Forbidden: Unauthenticated user attempted to star.
        404 Not Found: Project with given UUID not found.
    """
    project = get_object_or_404(
        Project.objects.prefetch_related("starred_by", "tags"), pk=project_id,
    )
    with transaction.atomic():
        if project.starred_by.filter(pk=request.user.pk).exists():
            project.starred_by.remove(request.user)
        else:
            project.starred_by.add(request.user)
        serializer = ProjectSerializer(project, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPortfolioOwnerOrEditorOrReadOnly])
def experience_list(request: Request) -> Response:
    """Retrieve list of experiences or create a new experience.

    Supports filtering by title query and category. Mutating requests (POST)
    require portfolio owner (superuser) role and are executed inside an atomic transaction.

    Args:
        request (Request): The incoming REST request.

    Query Params:
        title (str, optional): Filter experiences by title (case-insensitive substring).
        q (str, optional): Alternative search query for title.
        category (str, optional): Filter experiences by category slug.

    Returns:
        Response: List of serialized experiences (200 OK) or newly created experience (201 Created).

    Error Codes:
        200 OK: Experience list successfully retrieved.
        201 Created: New experience successfully created.
        400 Bad Request: Invalid input data failed serializer validation.
        403 Forbidden: Non-superuser attempted creation.
    """
    if request.method in ("GET", "HEAD"):
        experiences = Experience.objects.prefetch_related("starred_by").order_by(
            "-started_at", "title", "id"
        )
        title = (
            request.query_params.get("title", "").strip()
            or request.query_params.get("q", "").strip()
        )
        category = request.query_params.get("category", "").strip()
        if title:
            experiences = experiences.filter(title__icontains=title)
        if category and category.lower() != "all":
            experiences = experiences.filter(category=category)
        serializer = ExperienceSerializer(
            experiences, many=True, context={"request": request},
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    with transaction.atomic():
        serializer = ExperienceSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPortfolioOwnerOrEditorOrReadOnly])
def experience_detail(request: Request, experience_id: uuid.UUID) -> Response:
    """Retrieve, update, or delete a specific experience.

    Read operations are public. PUT and PATCH operations are allowed for
    Portfolio Owner (superuser) and Editors. DELETE operations are restricted
    strictly to the Portfolio Owner (superuser). Mutating actions are executed
    inside an atomic transaction.

    Args:
        request (Request): The incoming REST request.
        experience_id (uuid.UUID): Primary key of the experience.

    Returns:
        Response: Serialized experience data (200 OK) or empty body (204 No Content).

    Error Codes:
        200 OK: Experience details retrieved or updated successfully.
        204 No Content: Experience successfully deleted.
        400 Bad Request: Invalid update payload failed serializer validation.
        403 Forbidden: Request lacking required role permissions.
        404 Not Found: Experience with given UUID not found.
    """
    experience = get_object_or_404(
        Experience.objects.prefetch_related("starred_by"), pk=experience_id,
    )
    if request.method in ("GET", "HEAD"):
        serializer = ExperienceSerializer(experience, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "DELETE":
        with transaction.atomic():
            experience.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    with transaction.atomic():
        serializer = ExperienceSerializer(
            experience,
            data=request.data,
            partial=request.method == "PATCH",
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def experience_star(request: Request, experience_id: uuid.UUID) -> Response:
    """Toggle star status on a specific experience for the authenticated user.

    Accessible to any authenticated user (regular user, editor, or superuser).
    Executed within an atomic transaction.

    Args:
        request (Request): The incoming REST request.
        experience_id (uuid.UUID): Primary key of the experience.

    Returns:
        Response: Updated serialized experience data with refreshed star status (200 OK).

    Error Codes:
        200 OK: Star status successfully toggled.
        403 Forbidden: Unauthenticated user attempted to star.
        404 Not Found: Experience with given UUID not found.
    """
    experience = get_object_or_404(
        Experience.objects.prefetch_related("starred_by"), pk=experience_id,
    )
    with transaction.atomic():
        if experience.starred_by.filter(pk=request.user.pk).exists():
            experience.starred_by.remove(request.user)
        else:
            experience.starred_by.add(request.user)
        serializer = ExperienceSerializer(experience, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["GET", "HEAD", "POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPortfolioOwnerOrEditorOrReadOnly])
def skill_list(request: Request) -> Response:
    """Retrieve list of skills or create a new skill.

    Args:
        request (Request): The incoming REST request.

    Query Params:
        title (str, optional): Filter skills by title substring.
        level (str, optional): Filter skills by level name.

    Returns:
        Response: List of serialized skills (200 OK) or newly created skill (201 Created).

    Error Codes:
        200 OK: Skill list successfully retrieved.
        201 Created: New skill successfully created.
        400 Bad Request: Invalid input data failed serializer validation.
        403 Forbidden: Non-superuser attempted creation.
    """
    if request.method in ("GET", "HEAD"):
        skills = Skill.objects.prefetch_related("starred_by").order_by("title", "id")
        title = request.query_params.get("title", "").strip()
        level = request.query_params.get("level", "").strip()
        if title:
            skills = skills.filter(title__icontains=title)
        if level and level.lower() != "all":
            skills = skills.filter(level__iexact=level)
        serializer = SkillSerializer(skills, many=True, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    with transaction.atomic():
        serializer = SkillSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


@api_view(["GET", "HEAD", "PUT", "PATCH", "DELETE"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsPortfolioOwnerOrEditorOrReadOnly])
def skill_detail(request: Request, skill_id: uuid.UUID) -> Response:
    """Retrieve, update, or delete a specific skill.

    Read operations are public. PUT and PATCH operations are allowed for
    Portfolio Owner (superuser) and Editors. DELETE operations are restricted
    strictly to the Portfolio Owner (superuser). Mutating actions are executed
    inside an atomic transaction.

    Args:
        request (Request): The incoming REST request.
        skill_id (uuid.UUID): Primary key of the skill.

    Returns:
        Response: Serialized skill data (200 OK) or empty body (204 No Content).

    Error Codes:
        200 OK: Skill details retrieved or updated successfully.
        204 No Content: Skill successfully deleted.
        400 Bad Request: Invalid update payload failed serializer validation.
        403 Forbidden: Request lacking required role permissions.
        404 Not Found: Skill with given UUID not found.
    """
    skill = get_object_or_404(
        Skill.objects.prefetch_related("starred_by"), pk=skill_id,
    )
    if request.method in ("GET", "HEAD"):
        serializer = SkillSerializer(skill, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    if request.method == "DELETE":
        with transaction.atomic():
            skill.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)

    with transaction.atomic():
        serializer = SkillSerializer(
            skill,
            data=request.data,
            partial=request.method == "PATCH",
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)


@api_view(["POST"])
@authentication_classes([SessionAuthentication])
@permission_classes([IsAuthenticated])
def skill_star(request: Request, skill_id: uuid.UUID) -> Response:
    """Toggle star status on a specific skill for the authenticated user.

    Accessible to any authenticated user (regular user, editor, or superuser).
    Executed within an atomic transaction.

    Args:
        request (Request): The incoming REST request.
        skill_id (uuid.UUID): Primary key of the skill.

    Returns:
        Response: Updated serialized skill data with refreshed star status (200 OK).

    Error Codes:
        200 OK: Star status successfully toggled.
        403 Forbidden: Unauthenticated user attempted to star.
        404 Not Found: Skill with given UUID not found.
    """
    skill = get_object_or_404(
        Skill.objects.prefetch_related("starred_by"), pk=skill_id,
    )
    with transaction.atomic():
        if skill.starred_by.filter(pk=request.user.pk).exists():
            skill.starred_by.remove(request.user)
        else:
            skill.starred_by.add(request.user)
        serializer = SkillSerializer(skill, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)
