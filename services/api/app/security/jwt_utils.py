from datetime import datetime, timedelta, timezone
from uuid import UUID

from jose import JWTError, jwt

from app.config import get_settings
from app.models.user import User, UserRole


def create_access_token(user: User) -> str:
    s = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=s.access_token_expire_minutes)
    payload = {
        "sub": str(user.id),
        "role": user.role.value,
        "exp": expire,
    }
    return jwt.encode(payload, s.jwt_secret, algorithm=s.jwt_algorithm)


def decode_token(token: str) -> tuple[UUID, UserRole]:
    s = get_settings()
    try:
        data = jwt.decode(token, s.jwt_secret, algorithms=[s.jwt_algorithm])
        uid = UUID(data["sub"])
        role = UserRole(data["role"])
        return uid, role
    except (JWTError, KeyError, ValueError) as e:
        raise ValueError("Invalid token") from e
