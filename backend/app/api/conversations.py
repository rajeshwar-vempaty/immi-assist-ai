"""Conversation history API — authenticated users only."""

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.deps import require_user
from app.db.base import get_db
from app.models.models import User
from app.services import conversation_service as convs

router = APIRouter(prefix="/conversations", tags=["Conversations"])


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New conversation", max_length=255)


@router.get("")
def list_conversations(user: User = Depends(require_user), db: Session = Depends(get_db)):
    return {"conversations": convs.list_conversations(db, user)}


@router.post("")
def create_conversation(
    body: CreateConversationRequest,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    conv = convs.create_conversation(db, user, body.title)
    return {"id": conv.id, "title": conv.title}


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    return convs.conversation_detail(db, user, conversation_id)


@router.delete("/{conversation_id}")
def delete_conversation(
    conversation_id: str,
    user: User = Depends(require_user),
    db: Session = Depends(get_db),
):
    convs.delete_conversation(db, user, conversation_id)
    return {"status": "deleted"}
