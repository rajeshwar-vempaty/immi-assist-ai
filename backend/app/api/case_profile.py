"""Case profile API — GET/PUT immigration case context."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.db.base import get_db
from app.models.models import User
from app.schemas.schemas import CaseProfileResponse, CaseProfileUpdate
from app.services import case_profile_service as profiles

router = APIRouter(prefix="/case-profile", tags=["Case Profile"])


@router.get("", response_model=CaseProfileResponse)
def get_case_profile(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return profiles.get_profile(db, user)


@router.put("", response_model=CaseProfileResponse)
def update_case_profile(
    body: CaseProfileUpdate,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    return profiles.upsert_profile(db, user, body)
