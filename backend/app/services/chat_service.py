"""Chat service — authenticated user chat with provider routing and conversation persistence."""

import logging
import re
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.llm_router import Intent
from app.core.prompts import (
    CHECKLIST_PROMPT,
    POLICY_QA_PROMPT,
    RFE_ANALYSIS_PROMPT,
    TIMELINE_PROMPT,
)
from app.models.models import Message, User
from app.providers import get_provider
from app.schemas.schemas import ChatRequest, ChatResponse
from app.services import conversation_service as convs
from app.services import credentials_service as creds
from app.services.llm_json_service import extract_json
from app.services.rag_service import get_rag_service
from app.utils.citations import format_citations
from app.utils.disclaimer import CASE_SPECIFIC_REDIRECT, check_confidence, inject_disclaimer

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
            lines.append(
                f"- **{item.get('document', 'Document')}** ({mark}): {item.get('description', '')}"
            )
            if item.get("tips"):
                lines.append(f"  - Tip: {item['tips']}")
        lines.append("")
    mistakes = data.get("common_mistakes") or []
    if mistakes:
        lines.append("**Common mistakes:**")
        lines.extend([f"- {m}" for m in mistakes])
    return "\n".join(lines)


def _humanize_structured_response(intent: Intent, content: str) -> str:
    if intent not in (Intent.TIMELINE, Intent.CHECKLIST):
        return content
    try:
        data = extract_json(content)
    except Exception:
        return content
    if intent == Intent.TIMELINE:
        return _format_timeline_text(data)
    return _format_checklist_text(data)


def _keyword_intent(message: str) -> Intent:
    lower = message.lower()
    if any(k in lower for k in ["rfe", "request for evidence", "noid"]):
        return Intent.RFE_HELP
    if any(k in lower for k in ["documents", "checklist", "what do i need", "paperwork"]):
        return Intent.CHECKLIST
    if any(k in lower for k in ["how long", "processing time", "timeline", "timelines", "approval"]):
        return Intent.TIMELINE
    if any(k in lower for k in ["my case", "my application", "my receipt"]):
        return Intent.CASE_SPECIFIC
    return Intent.POLICY_QA


class ChatService:
    def __init__(self, db: Session, user: User):
        self.db = db
        self.user = user
        self.rag_service = get_rag_service()

    async def process(self, request: ChatRequest) -> ChatResponse:
        provider, model, api_key = creds.resolve_provider_model(
            self.db,
            self.user,
            request.provider,
            request.model,
        )

        if request.conversation_id:
            conversation = convs.get_conversation(self.db, self.user, request.conversation_id)
        else:
            conversation = convs.create_conversation(self.db, self.user)

        convs.add_message(self.db, conversation, role="user", content=request.message)

        intent = _keyword_intent(request.message)
        confidence = 0.7

        if intent == Intent.CASE_SPECIFIC:
            response_text = CASE_SPECIFIC_REDIRECT
            convs.add_message(
                self.db,
                conversation,
                role="assistant",
                content=response_text,
                provider="system",
                model="system",
                intent=intent.value,
            )
            return ChatResponse(
                response=response_text,
                intent=intent.value,
                confidence=confidence,
                model_used="system",
                provider="system",
                sources=[],
                requires_lawyer=True,
                conversation_id=conversation.id,
                session_id=conversation.id,
            )

        collection = "processing_times" if intent == Intent.TIMELINE else "uscis_policy"
        retrieved_docs = self.rag_service.retrieve(
            query=request.message,
            n_results=5,
            collection_name=collection,
        )
        context, sources = self.rag_service.format_context(retrieved_docs)

        prior = (
            self.db.query(Message)
            .filter(Message.conversation_id == conversation.id)
            .order_by(Message.created_at.asc())
            .all()
        )
        # Exclude the user message we just persisted
        history_msgs = [{"role": m.role, "content": m.content} for m in prior[:-1]][-6:]
        if not history_msgs and request.chat_history:
            history_msgs = [
                {"role": m.role, "content": m.content} for m in request.chat_history[-6:]
            ]

        chat_history_str = "\n".join(
            [f"{msg['role']}: {msg['content']}" for msg in history_msgs]
        )

        if intent == Intent.CHECKLIST:
            system_prompt = CHECKLIST_PROMPT.format(
                visa_type="Unknown",
                details=request.message,
                context=context,
            )
        elif intent == Intent.RFE_HELP:
            system_prompt = RFE_ANALYSIS_PROMPT.format(
                rfe_text=request.message,
                petition_type="Unknown",
                context=context,
            )
        elif intent == Intent.TIMELINE:
            system_prompt = TIMELINE_PROMPT.format(
<<<<<<< HEAD
                form_type=_resolve_timeline_form_type(classified.sub_topic, request.message),
=======
                form_type=request.message,
>>>>>>> e070972 (feat(auth): Google login, user-scoped history, encrypted BYOK keys)
                service_center="Unknown",
                filing_date="Not provided",
                category="General",
                processing_data=context,
                context=context,
            )
        else:
            system_prompt = POLICY_QA_PROMPT.format(
                context=context,
                question=request.message,
                chat_history=chat_history_str or "No prior history.",
            )

        adapter = get_provider(provider)
        result = await adapter.chat(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            user_message=request.message,
            history=history_msgs,
        )

        response_text = _humanize_structured_response(intent, result.content)
        confidence_warning = check_confidence(confidence)
        if confidence_warning:
            response_text = confidence_warning + "\n\n" + response_text

        disclaimer_type = {
            Intent.RFE_HELP: "rfe",
            Intent.TIMELINE: "timeline",
        }.get(intent, "standard")
        response_text = inject_disclaimer(response_text, disclaimer_type)
        citation_block = format_citations(sources)
        if citation_block and citation_block not in response_text:
            response_text = response_text + citation_block

        convs.add_message(
            self.db,
            conversation,
            role="assistant",
            content=response_text,
            provider=provider,
            model=model,
            intent=intent.value,
            sources=sources,
        )

        return ChatResponse(
            response=response_text,
            intent=intent.value,
            confidence=confidence,
            model_used=model,
            provider=provider,
            sources=sources,
            requires_lawyer=False,
            conversation_id=conversation.id,
            session_id=conversation.id,
            timestamp=datetime.utcnow(),
        )
