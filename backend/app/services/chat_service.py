"""Chat service — intent classification, RAG, LLM routing, persistence."""

import json
import logging
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.deps import AuthContext
from app.core.llm_router import Intent, get_llm_router
from app.core.prompts import (
    CHECKLIST_PROMPT,
    POLICY_QA_PROMPT,
    RFE_ANALYSIS_PROMPT,
    TIMELINE_PROMPT,
)
from app.models.models import ChatMessage, ChatSession
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services.rag_service import get_rag_service
from app.utils.citations import format_citations
from app.utils.disclaimer import inject_disclaimer, check_confidence, CASE_SPECIFIC_REDIRECT

logger = logging.getLogger(__name__)


class ChatService:
    def __init__(self, db: Session, auth: AuthContext):
        self.db = db
        self.auth = auth
        self.llm_router = get_llm_router()
        self.rag_service = get_rag_service()

    def _get_or_create_session(self, session_id: str | None) -> ChatSession:
        if session_id:
            existing = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if existing:
                return existing

        session = ChatSession(
            user_id=self.auth.user.id if self.auth.user else None,
            anonymous_session_id=self.auth.anonymous_session_id if not self.auth.user else None,
        )
        self.db.add(session)
        self.db.commit()
        self.db.refresh(session)
        return session

    def _save_message(
        self,
        session: ChatSession,
        role: str,
        content: str,
        intent: str | None = None,
        model_used: str | None = None,
        sources: list[str] | None = None,
    ) -> None:
        msg = ChatMessage(
            session_id=session.id,
            role=role,
            content=content,
            intent=intent,
            model_used=model_used,
            sources_json=json.dumps(sources or []),
        )
        self.db.add(msg)
        self.db.commit()

    async def process(self, request: ChatRequest) -> ChatResponse:
        classified = await self.llm_router.classify_intent(request.message)
        logger.info(
            f"Intent: {classified.intent} | Confidence: {classified.confidence}"
        )

        session = self._get_or_create_session(request.session_id)
        self._save_message(session, "user", request.message)

        if classified.intent == Intent.CASE_SPECIFIC:
            response = ChatResponse(
                response=CASE_SPECIFIC_REDIRECT,
                intent=classified.intent.value,
                confidence=classified.confidence,
                model_used="system",
                sources=[],
                requires_lawyer=True,
                session_id=session.id,
            )
            self._save_message(session, "assistant", response.response, intent=response.intent)
            return response

        collection = "uscis_policy"
        if classified.intent == Intent.TIMELINE:
            collection = "processing_times"

        retrieved_docs = self.rag_service.retrieve(
            query=request.message,
            n_results=5,
            collection_name=collection,
        )
        context, sources = self.rag_service.format_context(retrieved_docs)

        chat_history_str = "\n".join(
            [f"{msg.role}: {msg.content}" for msg in request.chat_history[-6:]]
        )

        if classified.intent in (Intent.POLICY_QA, Intent.GENERAL):
            system_prompt = POLICY_QA_PROMPT.format(
                context=context,
                question=request.message,
                chat_history=chat_history_str or "No prior history.",
            )
        elif classified.intent == Intent.CHECKLIST:
            system_prompt = CHECKLIST_PROMPT.format(
                visa_type=classified.visa_type or "Unknown",
                details=request.message,
                context=context,
            )
        elif classified.intent == Intent.RFE_HELP:
            system_prompt = RFE_ANALYSIS_PROMPT.format(
                rfe_text=request.message,
                petition_type=classified.visa_type or "Unknown",
                context=context,
            )
        elif classified.intent == Intent.TIMELINE:
            system_prompt = TIMELINE_PROMPT.format(
                form_type=classified.sub_topic or request.message,
                service_center="Unknown",
                filing_date="Not provided",
                category=classified.visa_type or "General",
                processing_data=context,
                context=context,
            )
        else:
            system_prompt = POLICY_QA_PROMPT.format(
                context=context,
                question=request.message,
                chat_history=chat_history_str or "No prior history.",
            )

        llm_response = await self.llm_router.route_and_respond(
            user_message=request.message,
            system_prompt=system_prompt,
            intent=classified.intent,
        )

        response_text = llm_response.content
        confidence_warning = check_confidence(classified.confidence)
        if confidence_warning:
            response_text = confidence_warning + "\n\n" + response_text

        disclaimer_type = {
            Intent.RFE_HELP: "rfe",
            Intent.TIMELINE: "timeline",
        }.get(classified.intent, "standard")
        response_text = inject_disclaimer(response_text, disclaimer_type)

        citation_block = format_citations(sources)
        if citation_block and citation_block not in response_text:
            response_text = response_text + citation_block

        response = ChatResponse(
            response=response_text,
            intent=classified.intent.value,
            confidence=classified.confidence,
            model_used=llm_response.model_used,
            sources=sources,
            requires_lawyer=classified.requires_lawyer,
            session_id=session.id,
            timestamp=datetime.utcnow(),
        )
        self._save_message(
            session,
            "assistant",
            response.response,
            intent=response.intent,
            model_used=response.model_used,
            sources=sources,
        )
        return response
