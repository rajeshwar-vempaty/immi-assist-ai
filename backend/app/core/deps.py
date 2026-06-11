"""FastAPI dependencies for auth and database."""

import uuid
from dataclasses import dataclass
from typing import Optional

from fastapi import Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.security import hash_api_key
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
    def identity_key(self) -> tuple[str, str]:
        """Return (type, id) for rate limiting: user or anonymous."""
        if self.user:
            return ("user", self.user.id)
        return ("anonymous", self.anonymous_session_id or "")


def get_or_create_anonymous_session(request: Request, response=None) -> str:
    """Get anonymous session ID from header or assign new one."""
    session_id = request.headers.get("X-Session-ID")
    if not session_id:
        session_id = str(uuid.uuid4())
    request.state.anonymous_session_id = session_id
    return session_id


async def get_auth_context(
    request: Request,
    x_api_key: Optional[str] = Header(None, alias="X-API-Key"),
    x_session_id: Optional[str] = Header(None, alias="X-Session-ID"),
    db: Session = Depends(get_db),
) -> AuthContext:
    """Resolve user from API key or anonymous session."""
    user = None
    api_key_id = None

    if x_api_key:
        key_hash = hash_api_key(x_api_key)
        api_key = (
            db.query(ApiKey)
            .filter(ApiKey.key_hash == key_hash, ApiKey.active.is_(True))
            .first()
        )
        if api_key:
            user = db.query(User).filter(User.id == api_key.user_id).first()
            api_key_id = api_key.id

    anonymous_session_id = x_session_id
    if not user:
        anonymous_session_id = get_or_create_anonymous_session(request)
        request.state.anonymous_session_id = anonymous_session_id

    return AuthContext(
        user=user,
        anonymous_session_id=anonymous_session_id if not user else None,
        api_key_id=api_key_id,
    )
