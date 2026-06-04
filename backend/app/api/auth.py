"""Authentication and API key management."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, get_auth_context
from app.core.security import generate_api_key, hash_api_key
from app.db.base import get_db
from app.models.models import ApiKey, User
from app.services.usage_service import count_usage_last_24h, get_daily_limit

router = APIRouter(prefix="/auth", tags=["Auth"])


class RegisterRequest(BaseModel):
    email: str | None = None
    tier: str = Field(default="starter", pattern="^(free|starter)$")


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


@router.post("/register", response_model=RegisterResponse)
def register(request: RegisterRequest, db: Session = Depends(get_db)):
    user = User(email=request.email, tier=request.tier)
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
    db.commit()

    return RegisterResponse(
        user_id=user.id,
        api_key=api_key,
        tier=user.tier,
        daily_limit=get_daily_limit(user.tier),
    )


@router.get("/me", response_model=MeResponse)
def me(auth: AuthContext = Depends(get_auth_context), db: Session = Depends(get_db)):
    usage = count_usage_last_24h(db, auth)
    return MeResponse(
        user_id=auth.user.id if auth.user else None,
        tier=auth.tier,
        daily_limit=get_daily_limit(auth.tier),
        usage_last_24h=usage,
        authenticated=auth.user is not None,
    )
