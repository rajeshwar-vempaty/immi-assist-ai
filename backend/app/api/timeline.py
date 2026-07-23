"""Processing timeline API."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, require_user
from app.db.base import get_db
from app.models.models import User
from app.schemas.schemas import TimelineRequest, TimelineResponse
from app.services import uscis_times_service as uscis
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


@router.get("/timeline/uscis/forms")
async def uscis_forms(user: User = Depends(require_user)):
    return await uscis.get_forms()


@router.get("/timeline/uscis/categories")
async def uscis_categories(
    form: str = Query(..., min_length=2, max_length=16),
    user: User = Depends(require_user),
):
    return await uscis.get_categories(form)


@router.get("/timeline/uscis/offices")
async def uscis_offices(
    form: str = Query(..., min_length=2, max_length=16),
    category: str = Query(..., min_length=1, max_length=64),
    user: User = Depends(require_user),
):
    return await uscis.get_offices(form, category)


@router.get("/timeline/uscis/processing-time")
async def uscis_processing_time(
    form: str = Query(..., min_length=2, max_length=16),
    category: str = Query(..., min_length=1, max_length=64),
    office: str = Query(..., min_length=1, max_length=64),
    user: User = Depends(require_user),
):
    return await uscis.get_processing_time(form, category, office)
