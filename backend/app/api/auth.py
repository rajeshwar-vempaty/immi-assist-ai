"""Authentication — Google sign-in, session JWT, profile."""

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import AuthContext, get_auth_context
from app.core.exceptions import AuthError
from app.db.base import get_db
from app.models.models import User
from app.services.google_auth import (
    issue_session_token,
    upsert_dev_user,
    upsert_google_user,
    verify_google_id_token,
)
from app.services.usage_service import count_usage_last_24h, get_daily_limit

router = APIRouter(prefix="/auth", tags=["Auth"])


class GoogleLoginRequest(BaseModel):
    id_token: str = Field(..., min_length=20)


class DevLoginRequest(BaseModel):
    email: str = Field(..., min_length=3)
    name: str | None = None


class AuthUserResponse(BaseModel):
    id: str
    email: str | None
    name: str | None
    picture: str | None
    tier: str
    authenticated: bool = True
    daily_limit: int
    usage_last_24h: int


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: AuthUserResponse


def _user_response(db: Session, user: User, auth: AuthContext | None = None) -> AuthUserResponse:
    ctx = auth or AuthContext(user=user, anonymous_session_id=None, api_key_id=None)
    return AuthUserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        picture=user.picture,
        tier=user.tier,
        daily_limit=get_daily_limit(user.tier),
        usage_last_24h=count_usage_last_24h(db, ctx),
    )


def _set_session_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.app_env == "production",
        max_age=settings.jwt_expire_hours * 3600,
        path="/",
    )


@router.post("/google", response_model=LoginResponse)
def login_with_google(
    body: GoogleLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    claims = verify_google_id_token(body.id_token)
    user = upsert_google_user(db, claims)
    token = issue_session_token(user)
    _set_session_cookie(response, token)
    return LoginResponse(access_token=token, user=_user_response(db, user))


@router.post("/dev-login", response_model=LoginResponse)
def login_dev(
    body: DevLoginRequest,
    response: Response,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    if not settings.auth_dev_mode:
        raise AuthError("Dev login is disabled. Use Google sign-in.", status_code=403)
    user = upsert_dev_user(db, body.email, body.name)
    token = issue_session_token(user)
    _set_session_cookie(response, token)
    return LoginResponse(access_token=token, user=_user_response(db, user))


@router.get("/me", response_model=AuthUserResponse)
def me(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise AuthError("Not authenticated.", status_code=401)
    return _user_response(db, auth.user, auth)


@router.post("/logout")
def logout(response: Response):
    settings = get_settings()
    response.delete_cookie(settings.session_cookie_name, path="/")
    return {"status": "signed_out"}


@router.get("/config")
def auth_config():
    settings = get_settings()
    return {
        "google_client_id": settings.google_client_id or None,
        "auth_dev_mode": settings.auth_dev_mode,
    }
