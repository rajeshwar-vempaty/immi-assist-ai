"""FastAPI dependencies for auth and database."""

from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthError
from app.core.security import decode_access_token, hash_api_key
from app.db.base import get_db
from app.models.models import ApiKey, User


@dataclass
class AuthContext:
    user: Optional[User]
    anonymous_session_id: Optional[str]
    api_key_id: Optional[str]

    @property
    def tier(self) -> str:
        if self.user:
            return self.user.tier
        return "free"

    @property
    def is_authenticated(self) -> bool:
        return self.user is not None


def _extract_bearer(authorization: Optional[str]) -> Optional[str]:
    if not authorization:
        return None
    parts = authorization.split(" ", 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return None


def _user_from_token(db: Session, token: str) -> User:
    payload = decode_access_token(token)
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise AuthError("Session expired or invalid. Please sign in again.", status_code=401)
    return user


async def get_auth_context(
    request: Request,
    authorization: Optional[str] = Header(None),
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Resolve authenticated user from JWT cookie/header or legacy platform API key."""
    settings = get_settings()
    user = None
    api_key_id = None

    bearer = _extract_bearer(authorization)
    cookie_token = request.cookies.get(settings.session_cookie_name)
    token = bearer or cookie_token
    if token:
        # Invalid/expired session tokens must not silently become anonymous.
        user = _user_from_token(db, token)

    if not user and x_api_key:
        key_hash = hash_api_key(x_api_key)
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.active.is_(True))
            .first()
        )
        if api_key:
            user = db.query(User).filter(User.id == api_key.user_id).first()
            api_key_id = api_key.id

    return AuthContext(user=user, anonymous_session_id=None, api_key_id=api_key_id)


async def require_user(auth: AuthContext = Depends(get_auth_context)) -> User:
    if not auth.user:
        raise AuthError("Authentication required. Please sign in.", status_code=401)
    return auth.user
