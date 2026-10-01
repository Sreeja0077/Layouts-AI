"""
Role-Based Access Control (RBAC) permission guards.
Restricts API endpoints based on required user roles and organization multi-tenancy.
"""

from typing import List
from fastapi import Depends, HTTPException, status
from app.security.auth import AuthenticatedUser, UserRole, get_current_user


class RoleChecker:
    """Dependency callable enforcing that current user has one of the allowed roles."""

    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, current_user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if current_user.role not in self.allowed_roles and current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Forbidden: User role '{current_user.role.value}' lacks required permissions. "
                    f"Allowed roles: {[r.value for r in self.allowed_roles]}"
                ),
            )
        return current_user


def require_roles(allowed_roles: List[UserRole]):
    """Helper factory creating a RoleChecker dependency."""
    return Depends(RoleChecker(allowed_roles))
