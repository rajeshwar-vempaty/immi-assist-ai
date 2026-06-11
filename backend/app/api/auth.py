"""Authentication and API key management."""

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, get_auth_context
from app.core.exceptions import AuthError
from app.db.base import get_db
from app.models.models import ApiKey
from app.services.auth_service import create_api_key, register_user, revoke_api_key
from app.services.usage_service import count_usage_last_24h, get_daily_limit

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: str | None = None
    tier: str = Field(default="free", pattern="^(free|starter)$")


class RegisterResponse(BaseModel):
    user_id: str
    api_key: str
    tier: str
    daily_limit: int


class MeResponse(BaseModel):
    user_id: str | None
    tier: str
    daily_limit: int
    usage_last_24h: int
    authenticated: bool
    active_api_keys: int = 0


class CreateKeyRequest(BaseModel):
    name: str = Field(default="additional", max_length=128)


class CreateKeyResponse(BaseModel):
    api_key: str
    name: str


class ApiKeyInfo(BaseModel):
    id: str
    name: str
    created_at: str
    active: bool


class RevokeKeyResponse(BaseModel):
    status: str
    key_id: str


@router.post("/register", response_model=RegisterResponse)
def register(
    body: RegisterRequest,
    request: Request,
    x_admin_key: str | None = Header(None, alias="X-Admin-Key"),
    db: Session = Depends(get_db),
):
    user, api_key = register_user(
        db, request, body.email, body.tier, x_admin_key
    )
    return RegisterResponse(
        user_id=user.id,
        api_key=api_key,
        tier=user.tier,
        daily_limit=get_daily_limit(user.tier),
    )


@router.get("/me", response_model=MeResponse)
def me(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    if not auth.user:
        usage = count_usage_last_24h(db, auth)
        return MeResponse(
            user_id=None,
            tier=auth.tier,
            daily_limit=get_daily_limit(auth.tier),
            usage_last_24h=usage,
            authenticated=False,
            active_api_keys=0,
        )

    active_keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == auth.user.id, ApiKey.active.is_(True))
        .count()
    )
    usage = count_usage_last_24h(db, auth)
    return MeResponse(
        user_id=auth.user.id,
        tier=auth.tier,
        daily_limit=get_daily_limit(auth.tier),
        usage_last_24h=usage,
        authenticated=True,
        active_api_keys=active_keys,
    )


@router.get("/keys", response_model=list[ApiKeyInfo])
def list_keys(
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise AuthError("Authentication required.", status_code=401)

    keys = (
        db.query(ApiKey)
        .filter(ApiKey.user_id == auth.user.id)
        .order_by(ApiKey.created_at.desc())
        .all()
    )
    return [
        ApiKeyInfo(
            id=k.id,
            name=k.name,
            created_at=k.created_at.isoformat(),
            active=k.active,
        )
        for k in keys
    ]


@router.post("/keys", response_model=CreateKeyResponse)
def create_key(
    body: CreateKeyRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise AuthError("Authentication required.", status_code=401)

    api_key = create_api_key(db, auth.user, body.name)
    return CreateKeyResponse(api_key=api_key, name=body.name)


@router.delete("/keys/{key_id}", response_model=RevokeKeyResponse)
def revoke_key(
    key_id: str,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    if not auth.user:
        raise AuthError("Authentication required.", status_code=401)

    revoke_api_key(db, auth.user, key_id)
    return RevokeKeyResponse(status="revoked", key_id=key_id)
