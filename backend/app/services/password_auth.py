"""Email/password registration and login."""

from __future__ import annotations

import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AuthError
from app.core.security import hash_password, verify_password
from app.models.models import User, UserPreferences
from app.services.email_service import send_welcome_email
from app.services.google_auth import issue_session_token

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_password_user(
    db: Session,
    *,
    username: str,
    email: str,
    password: str,
) -> tuple[User, str, dict]:
    username = (username or "").strip()
    email = _normalize_email(email)
    if len(username) < 2:
        raise AuthError("Username must be at least 2 characters.", status_code=400)
    if not _EMAIL_RE.match(email):
        raise AuthError("Enter a valid email address.", status_code=400)
    if len(password) < 8:
        raise AuthError("Password must be at least 8 characters.", status_code=400)

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        raise AuthError("An account with this email already exists. Sign in instead.", status_code=409)

    user = User(
        email=email,
        name=username,
        password_hash=hash_password(password),
        tier="starter",
    )
    db.add(user)
    db.flush()
    db.add(UserPreferences(user_id=user.id))
    db.commit()
    db.refresh(user)

    email_result = send_welcome_email(to_email=email, name=username)
    token = issue_session_token(user)
    return user, token, email_result


def login_password_user(db: Session, *, email: str, password: str) -> tuple[User, str]:
    email = _normalize_email(email)
    user = db.query(User).filter(User.email == email).first()
    if not user or not user.password_hash:
        raise AuthError("Invalid email or password.", status_code=401)
    if not verify_password(password, user.password_hash):
        raise AuthError("Invalid email or password.", status_code=401)
    user.updated_at = datetime.utcnow()
    db.commit()
    return user, issue_session_token(user)
