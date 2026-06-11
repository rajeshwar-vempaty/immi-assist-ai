"""Document checklist API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, get_auth_context
from app.db.base import get_db
from app.schemas.schemas import ChecklistRequest, ChecklistResponse
from app.services.checklist_service import ChecklistService
from app.services.usage_service import check_rate_limit, record_usage

router = APIRouter()


@router.post("/checklist", response_model=ChecklistResponse)
async def create_checklist(
    request: ChecklistRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    check_rate_limit(db, auth)
    service = ChecklistService()
    result = await service.generate(request)
    record_usage(db, auth, "/checklist")
    return result
