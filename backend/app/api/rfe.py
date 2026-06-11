"""RFE analysis API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, get_auth_context
from app.db.base import get_db
from app.schemas.schemas import RFEAnalysis, RFERequest
from app.services.rfe_service import RFEService
from app.services.usage_service import check_rate_limit, record_usage

router = APIRouter()


@router.post("/rfe/analyze", response_model=RFEAnalysis)
async def analyze_rfe(
    request: RFERequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    check_rate_limit(db, auth)
    service = RFEService()
    result = await service.analyze(request)
    record_usage(db, auth, "/rfe/analyze")
    return result
