"""Document checklist API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, require_user
from app.db.base import get_db
from app.models.models import User
from app.schemas.schemas import ChecklistRequest, ChecklistResponse
from app.services.checklist_service import ChecklistService
from app.services.usage_service import check_rate_limit, record_usage

router = APIRouter()


@router.post("/checklist", response_model=ChecklistResponse)
async def create_checklist(
    request: ChecklistRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    auth = AuthContext(user=user, anonymous_session_id=None, api_key_id=None)
    check_rate_limit(db, auth)
    service = ChecklistService()
    result = await service.generate(request)
    record_usage(db, auth, "/checklist")
    return result
