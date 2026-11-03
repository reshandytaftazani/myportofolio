"""Custom DRF permission classes for portfolio access control (RBAC)."""

from typing import Any
from rest_framework.permissions import BasePermission, SAFE_METHODS
from rest_framework.request import Request
from rest_framework.views import APIView


class IsPortfolioOwnerOrReadOnly(BasePermission):
    """Permission class allowing full access to superusers and read-only access to others.

    Safe methods (GET, HEAD, OPTIONS) are open to public.
    Mutating methods (POST, PUT, PATCH, DELETE) require superuser privileges.
    """

    message = "Only the portfolio owner can change projects."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Check if request method is safe or if user is a superuser."""
        return (
            request.method in SAFE_METHODS
            or bool(request.user and request.user.is_superuser)
        )


class IsPortfolioOwnerOrEditorOrReadOnly(BasePermission):
    """Permission class implementing 4-role RBAC for portfolio resources.

    - Anonymous & Regular users: Read-only (GET, HEAD, OPTIONS).
    - Editors (in 'Editor' group): Read + Edit (PUT, PATCH).
    - Superusers (Portfolio owner): Full CRUD access (GET, POST, PUT, PATCH, DELETE).
    """

    message = "Only the portfolio owner or an editor can change this resource."

    def has_permission(self, request: Request, view: Any) -> bool:
        """Evaluate permission based on user role and HTTP method."""
        if request.method in SAFE_METHODS:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.is_superuser:
            return True
        return (
            request.method in ("PUT", "PATCH")
            and request.user.groups.filter(name="Editor").exists()
        )
