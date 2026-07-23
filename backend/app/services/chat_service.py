"""Chat service — intent classification, RAG, LLM routing, persistence."""

import json
import logging
import re
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
from app.services.llm_json_service import extract_json
from app.services.rag_service import get_rag_service
from app.utils.citations import format_citations
from app.utils.disclaimer import inject_disclaimer, check_confidence, CASE_SPECIFIC_REDIRECT

logger = logging.getLogger(__name__)

USCIS_FORM_RE = re.compile(r"\b((?:I|N|G|AR|EOIR|DS)[-\s]?\d{1,4}[A-Z]?)\b", re.IGNORECASE)


def _normalize_form_number(form_number: str) -> str:
    """Normalize USCIS-style form tokens like i129 or I 485 to I-129/I-485."""
    compact = re.sub(r"[-\s]", "", form_number).upper()
    match = re.fullmatch(r"([A-Z]+)(\d{1,4})([A-Z]?)", compact)
    if not match:
        return form_number.strip()
    prefix, number, suffix = match.groups()
    return f"{prefix}-{number}{suffix}"


def _resolve_timeline_form_type(sub_topic: str | None, message: str) -> str:
    """Prefer actual form numbers over visa labels for timeline prompts."""
    for candidate in (sub_topic, message):
        if not candidate:
            continue
        match = USCIS_FORM_RE.search(candidate)
        if match:
            return _normalize_form_number(match.group(1))

    return (sub_topic or message).strip()


def _format_timeline_text(data: dict) -> str:
    """Turn timeline JSON into readable chat text."""
    proc = data.get("current_processing_range") or data.get("processing_range_months") or {}
    min_m = proc.get("min_months", proc.get("min", "?"))
    max_m = proc.get("max_months", proc.get("max", "?"))
    completion = data.get("estimated_completion") or {}
    options = data.get("options_if_delayed") or []
    tips = data.get("tips") or []

    lines = [
        f"**{data.get('form_type', 'Form')} processing timeline**",
        "",
        f"- **Service center:** {data.get('service_center') or 'Not specified'}",
        f"- **Typical range:** {min_m}–{max_m} months",
        f"- **Case status:** {data.get('case_status', 'UNKNOWN')}",
    ]
    if completion:
        lines.append(
            f"- **Estimated completion:** {completion.get('earliest', '?')} to {completion.get('latest', '?')}"
        )
    if data.get("status_explanation"):
        lines.extend(["", data["status_explanation"]])
    if options:
        lines.extend(["", "**If delayed:**"])
        lines.extend([f"- {o}" for o in options])
    if tips:
        lines.extend(["", "**Tips:**"])
        lines.extend([f"- {t}" for t in tips])
    if data.get("data_as_of"):
        lines.extend(["", f"_Data as of: {data['data_as_of']}_"])
    return "\n".join(lines)


def _format_checklist_text(data: dict) -> str:
    """Turn checklist JSON into readable chat text."""
    lines = [
        f"**Document checklist: {data.get('visa_type', 'Visa')}**",
        f"Primary form: {data.get('form_number', 'N/A')}",
        f"Filing fee: {data.get('filing_fee', 'See USCIS')}",
        f"Estimated prep time: {data.get('estimated_prep_time', 'N/A')}",
        "",
    ]
    for cat in data.get("checklist") or []:
        lines.append(f"### {cat.get('category', 'Documents')}")
        for item in cat.get("items") or []:
            mark = "Required" if item.get("required", True) else "Optional"
            lines.append(f"- **{item.get('document', 'Document')}** ({mark}): {item.get('description', '')}")
            if item.get("tips"):
                lines.append(f"  - Tip: {item['tips']}")
        lines.append("")
    mistakes = data.get("common_mistakes") or []
    if mistakes:
        lines.append("**Common mistakes:**")
        lines.extend([f"- {m}" for m in mistakes])
    return "\n".join(lines)


def _humanize_structured_response(intent: Intent, content: str) -> str:
    """If the LLM returned JSON for checklist/timeline, format it for chat."""
    if intent not in (Intent.TIMELINE, Intent.CHECKLIST):
        return content
    try:
        data = extract_json(content)
    except Exception:
        return content
    if intent == Intent.TIMELINE:
        return _format_timeline_text(data)
    return _format_checklist_text(data)


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
                form_type=_resolve_timeline_form_type(classified.sub_topic, request.message),
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

        response_text = _humanize_structured_response(
            classified.intent, llm_response.content
        )
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
