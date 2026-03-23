"""Password hashing with the bcrypt library directly.

Avoids passlib + bcrypt>=4.1 compatibility issues (passlib reads bcrypt.__about__.__version__,
which newer bcrypt releases removed).
"""

import bcrypt


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False
