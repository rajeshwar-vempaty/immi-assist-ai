"""Processing timeline API."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, require_user
from app.db.base import get_db
from app.models.models import User
from app.schemas.schemas import TimelineRequest, TimelineResponse
from app.services.timeline_service import TimelineService
from app.services.usage_service import check_rate_limit, record_usage

router = APIRouter()


@router.post("/timeline", response_model=TimelineResponse)
async def estimate_timeline(
    request: TimelineRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    auth = AuthContext(user=user, anonymous_session_id=None, api_key_id=None)
    check_rate_limit(db, auth)
    service = TimelineService()
    result = await service.estimate(request)
    record_usage(db, auth, "/timeline")
    return result
