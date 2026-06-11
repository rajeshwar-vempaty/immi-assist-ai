"""Processing timeline API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, get_auth_context
from app.db.base import get_db
from app.schemas.schemas import TimelineRequest, TimelineResponse
from app.services.timeline_service import TimelineService
from app.services.usage_service import check_rate_limit, record_usage

router = APIRouter()


@router.post("/timeline", response_model=TimelineResponse)
async def estimate_timeline(
    request: TimelineRequest,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    check_rate_limit(db, auth)
    service = TimelineService()
    result = await service.estimate(request)
    record_usage(db, auth, "/timeline")
    return result
