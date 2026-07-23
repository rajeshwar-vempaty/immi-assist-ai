"""User settings — provider credentials and preferences."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.db.base import get_db
from app.models.models import User
from app.services import credentials_service as creds

router = APIRouter(prefix="/settings", tags=["Settings"])


class SaveCredentialRequest(BaseModel):
    api_key: str = Field(..., min_length=8, max_length=512)


class TestCredentialRequest(BaseModel):
    api_key: str | None = Field(None, min_length=8, max_length=512)


class PreferencesUpdate(BaseModel):
    default_provider: str | None = None
    default_model: str | None = None
    allow_fallback: bool | None = None


@router.get("/providers")
def providers_catalog(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return creds.get_preferences(db, user)


@router.get("/credentials")
def list_credentials(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return {"credentials": creds.list_credentials(db, user)}


@router.put("/credentials/{provider}")
async def save_credential(
    provider: str,
    body: SaveCredentialRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    return await creds.upsert_credential(db, user, provider.lower(), body.api_key)


@router.post("/credentials/{provider}/test")
async def test_credential(
    provider: str,
    body: TestCredentialRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    return await creds.test_credential(db, user, provider.lower(), body.api_key)


@router.delete("/credentials/{provider}")
def delete_credential(
    provider: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    creds.delete_credential(db, user, provider.lower())
    return {"status": "deleted", "provider": provider.lower()}


@router.get("/preferences")
def get_preferences(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return creds.get_preferences(db, user)


@router.put("/preferences")
def update_preferences(
    body: PreferencesUpdate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    return creds.update_preferences(
        db,
        user,
        body.default_provider,
        body.default_model,
        body.allow_fallback,
    )
