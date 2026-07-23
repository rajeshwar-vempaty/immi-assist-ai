"""RFE analysis API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, require_user
from app.db.base import get_db
from app.models.models import User
from app.schemas.schemas import RFEAnalysis, RFERequest
from app.services.rfe_service import RFEService
from app.services.usage_service import check_rate_limit, record_usage

router = APIRouter()


@router.post("/rfe/analyze", response_model=RFEAnalysis)
async def analyze_rfe(
    request: RFERequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    auth = AuthContext(user=user, anonymous_session_id=None, api_key_id=None)
    check_rate_limit(db, auth)
    service = RFEService()
    result = await service.analyze(request)
    record_usage(db, auth, "/rfe/analyze")
    return result
