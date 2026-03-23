"""Create default admin user for local development (idempotent)."""

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.user import User, UserRole
from app.security.pwd import hash_password


def main() -> None:
    url = os.environ.get("DATABASE_URL", "postgresql+psycopg2://prowler:prowler@localhost:5432/cloudaudit")
    engine = create_engine(url)
    Session = sessionmaker(bind=engine)
    db = Session()
    email = os.environ.get("SEED_ADMIN_EMAIL", "admin@example.com")
    password = os.environ.get("SEED_ADMIN_PASSWORD", "admin123!")
    if db.query(User).filter(User.email == email).first():
        print("Seed: user exists", email)
        return
    u = User(email=email, password_hash=hash_password(password), role=UserRole.admin)
    db.add(u)
    db.commit()
    print("Seed: created admin", email)


if __name__ == "__main__":
    main()
