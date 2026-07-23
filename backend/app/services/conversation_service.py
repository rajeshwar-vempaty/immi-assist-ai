"""User-scoped conversation persistence."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.models.models import Conversation, Message, User


def list_conversations(db: Session, user: User) -> list[dict]:
    rows = (
        db.query(Conversation)
        .filter(Conversation.user_id == user.id)
        .order_by(Conversation.updated_at.desc())
        .all()
    )
    return [
        {
            "id": row.id,
            "title": row.title,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
            "created_at": row.created_at.isoformat() if row.created_at else None,
        }
        for row in rows
    ]


def create_conversation(db: Session, user: User, title: str = "New conversation") -> Conversation:
    conv = Conversation(user_id=user.id, title=title[:255])
    db.add(conv)
    db.commit()
    db.refresh(conv)
    return conv


def get_conversation(db: Session, user: User, conversation_id: str) -> Conversation:
    conv = (
        db.query(Conversation)
        .filter(Conversation.id == conversation_id, Conversation.user_id == user.id)
        .first()
    )
    if not conv:
        raise AppError("Conversation not found.", status_code=404)
    return conv


def delete_conversation(db: Session, user: User, conversation_id: str) -> None:
    conv = get_conversation(db, user, conversation_id)
    db.delete(conv)
    db.commit()


def conversation_detail(db: Session, user: User, conversation_id: str) -> dict:
    conv = get_conversation(db, user, conversation_id)
    return {
        "id": conv.id,
        "title": conv.title,
        "updated_at": conv.updated_at.isoformat() if conv.updated_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "provider": m.provider,
                "model": m.model,
                "intent": m.intent,
                "sources": __import__("json").loads(m.sources_json or "[]"),
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in conv.messages
        ],
    }


def add_message(
    db: Session,
    conversation: Conversation,
    *,
    role: str,
    content: str,
    provider: str | None = None,
    model: str | None = None,
    intent: str | None = None,
    sources: list | None = None,
) -> Message:
    import json

    msg = Message(
        conversation_id=conversation.id,
        role=role,
        content=content,
        provider=provider,
        model=model,
        intent=intent,
        sources_json=json.dumps(sources or []),
    )
    db.add(msg)
    conversation.updated_at = datetime.utcnow()
    if role == "user" and (not conversation.title or conversation.title == "New conversation"):
        conversation.title = content[:80] + ("…" if len(content) > 80 else "")
    db.commit()
    db.refresh(msg)
    return msg
