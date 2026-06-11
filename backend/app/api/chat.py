"""
Chat API — Main conversational endpoint.
"""

import logging
from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, get_auth_context
from app.db.base import get_db
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.usage_service import check_rate_limit, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    response: Response,
    auth: AuthContext = Depends(get_auth_context),
    db: Session = Depends(get_db),
):
    check_rate_limit(db, auth)
    service = ChatService(db, auth)
    result = await service.process(request)
    record_usage(db, auth, "/chat")
    if auth.anonymous_session_id:
        response.headers["X-Session-ID"] = auth.anonymous_session_id
    return result
