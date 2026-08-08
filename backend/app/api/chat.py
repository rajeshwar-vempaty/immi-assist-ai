"""Chat API — authenticated conversational endpoint (JSON + SSE stream)."""

import json
import logging

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.deps import AuthContext, require_user
from app.db.base import get_db
from app.models.models import User
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.chat_service import ChatService
from app.services.usage_service import check_rate_limit, record_usage

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if request.session_id and not request.conversation_id:
        request.conversation_id = request.session_id

    auth = AuthContext(user=user, anonymous_session_id=None, api_key_id=None)
    check_rate_limit(db, auth)
    service = ChatService(db, user)
    result = await service.process(request)
    record_usage(db, auth, "/chat")
    return result


@router.post("/chat/stream")
async def chat_stream(
    request: ChatRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    if request.session_id and not request.conversation_id:
        request.conversation_id = request.session_id

    auth = AuthContext(user=user, anonymous_session_id=None, api_key_id=None)
    check_rate_limit(db, auth)
    service = ChatService(db, user)

    async def event_generator():
        try:
            async for event in service.stream(request):
                yield f"data: {json.dumps(event, default=str)}\n\n"
            record_usage(db, auth, "/chat/stream")
        except Exception as exc:
            logger.exception("Chat stream failed")
            err = {"type": "error", "message": str(exc) or "Chat stream failed"}
            yield f"data: {json.dumps(err)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
