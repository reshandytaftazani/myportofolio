"""Shared role checks for HTML views and JSON endpoints."""

from django.core.exceptions import PermissionDenied
from django.http import JsonResponse


def is_editor(user):
    return bool(
        user.is_authenticated
        and user.groups.filter(name="Editor").exists()
    )


def has_access(user, action):
    """Return whether a user may perform a portfolio action."""
    if action == "authenticated":
        return bool(user.is_authenticated)
    if not user.is_authenticated:
        return False

    if action == "star":
        return True
    if action in {"dashboard", "edit"}:
        return user.is_superuser or is_editor(user)
    if action in {"add", "delete"}:
        return user.is_superuser
    raise ValueError(f"Unknown access action: {action}")


def require_access(
    request,
    action,
    message="Anda tidak memiliki izin untuk melakukan tindakan ini.",
    *,
    json_response=False,
):
    """Raise on HTML denial; JSON endpoints explicitly request a 403 response."""
    if has_access(request.user, action):
        return None

    if json_response:
        return JsonResponse({"message": message}, status=403)
    raise PermissionDenied(message)
