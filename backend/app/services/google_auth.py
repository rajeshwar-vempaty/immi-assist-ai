"""Google authentication and session helpers."""

import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.security import create_access_token
from app.models.models import User, UserPreferences

logger = logging.getLogger(__name__)


def verify_google_id_token(id_token: str) -> dict:
    """Verify a Google Identity Services ID token and return claims."""
    settings = get_settings()
    if not settings.google_client_id:
        raise AuthError(
            "Google sign-in is not configured. Set GOOGLE_CLIENT_ID.",
            status_code=503,
        )
    try:
        from google.oauth2 import id_token as google_id_token
        from google.auth.transport import requests as google_requests

        claims = google_id_token.verify_oauth2_token(
            id_token,
            google_requests.Request(),
            settings.google_client_id,
        )
        if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
            raise AuthError("Invalid Google token issuer.", status_code=401)
        if not claims.get("email"):
            raise AuthError("Google account email is required.", status_code=401)
        return claims
    except AuthError:
        raise
    except Exception as exc:
        logger.warning("Google token verification failed")
        raise AuthError("Google login failed. Please try again.", status_code=401) from exc


def upsert_google_user(db: Session, claims: dict) -> User:
    sub = claims.get("sub")
    email = claims.get("email")
    name = claims.get("name") or email
    picture = claims.get("picture")

    user = None
    if sub:
        user = db.query(User).filter(User.google_sub == sub).first()
    if not user and email:
        user = db.query(User).filter(User.email == email).first()

    if user:
        user.google_sub = sub or user.google_sub
        user.email = email or user.email
        user.name = name or user.name
        user.picture = picture or user.picture
        user.updated_at = datetime.utcnow()
    else:
        user = User(
            google_sub=sub,
            email=email,
            name=name,
            picture=picture,
            tier="starter",
        )
        db.add(user)
        db.flush()
        db.add(UserPreferences(user_id=user.id))

    db.commit()
    db.refresh(user)
    return user


def upsert_dev_user(db: Session, email: str, name: str | None = None) -> User:
    settings = get_settings()
    if not settings.auth_dev_mode and settings.app_env == "production":
        raise AuthError("Dev login is disabled.", status_code=403)

    user = db.query(User).filter(User.email == email).first()
    if user:
        user.name = name or user.name or email.split("@")[0]
        user.updated_at = datetime.utcnow()
    else:
        user = User(
            email=email,
            name=name or email.split("@")[0],
            google_sub=f"dev:{email}",
            tier="starter",
        )
        db.add(user)
        db.flush()
        db.add(UserPreferences(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


def issue_session_token(user: User) -> str:
    return create_access_token(user.id, extra={"email": user.email})
