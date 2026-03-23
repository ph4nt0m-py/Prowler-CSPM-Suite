from app.models.user import User, UserRole


def require_admin(user: User) -> None:
    if user.role != UserRole.admin:
        raise PermissionError("Admin role required")
