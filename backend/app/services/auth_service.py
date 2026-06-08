"""Authentication business logic with registration limits."""

from datetime import datetime, timedelta

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.security import generate_api_key, hash_api_key
from app.models.models import ApiKey, RegistrationLog, User


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _verify_admin_key(admin_key: str | None) -> bool:
    settings = get_settings()
    return bool(
        settings.admin_api_key
        and admin_key
        and admin_key == settings.admin_api_key
    )


def _count_registrations_for_ip(db: Session, ip: str) -> int:
    since = datetime.utcnow() - timedelta(hours=24)
    return (
        db.query(RegistrationLog)
        .filter(RegistrationLog.ip_address == ip, RegistrationLog.created_at >= since)
        .count()
    )


def _count_active_keys(db: Session, user_id: str) -> int:
    return (
        db.query(ApiKey)
        .filter(ApiKey.user_id == user_id, ApiKey.active.is_(True))
        .count()
    )


def register_user(
    db: Session,
    request: Request,
    email: str | None,
    tier: str,
    admin_key: str | None,
) -> tuple[User, str]:
    """
    Register a user and return (user, plaintext_api_key).

    Public registration (when enabled) is limited to free tier.
    Admin registration requires X-Admin-Key and allows starter tier.
    """
    settings = get_settings()
    ip = _client_ip(request)
    is_admin = _verify_admin_key(admin_key)

    if not is_admin:
        if not settings.allow_public_registration:
            raise AuthError(
                "Registration requires admin authorization. Contact support for an API key.",
                status_code=403,
            )
        tier = "free"
        if _count_registrations_for_ip(db, ip) >= settings.max_registrations_per_ip_per_day:
            raise AuthError(
                "Registration limit reached for this network. Try again tomorrow.",
                status_code=429,
            )

    if email:
        existing = db.query(User).filter(User.email == email).first()
        if existing:
            raise AuthError("An account with this email already exists.", status_code=409)

    user = User(email=email, tier=tier if is_admin else "free")
    db.add(user)
    db.commit()
    db.refresh(user)

    api_key = generate_api_key()
    db.add(
        ApiKey(
            user_id=user.id,
            key_hash=hash_api_key(api_key),
            name="default",
        )
    )
    db.add(
        RegistrationLog(
            ip_address=ip,
            email=email,
            user_id=user.id,
        )
    )
    db.commit()

    return user, api_key


def create_api_key(
    db: Session,
    user: User,
    name: str = "additional",
) -> str:
    """Create an additional API key for an authenticated user."""
    settings = get_settings()
    if _count_active_keys(db, user.id) >= settings.max_api_keys_per_user:
        raise AuthError(
            f"Maximum of {settings.max_api_keys_per_user} active API keys allowed.",
            status_code=400,
        )

    api_key = generate_api_key()
    db.add(
        ApiKey(
            user_id=user.id,
            key_hash=hash_api_key(api_key),
            name=name,
        )
    )
    db.commit()
    return api_key


def revoke_api_key(db: Session, user: User, key_id: str) -> None:
    """Deactivate an API key belonging to the user."""
    api_key = (
        db.query(ApiKey)
        .filter(ApiKey.id == key_id, ApiKey.user_id == user.id, ApiKey.active.is_(True))
        .first()
    )
    if not api_key:
        raise AuthError("API key not found.", status_code=404)

    active_count = _count_active_keys(db, user.id)
    if active_count <= 1:
        raise AuthError("Cannot revoke your only active API key.", status_code=400)

    api_key.active = False
    db.commit()
