"""
Chat API — Main conversational endpoint.

Handles the full pipeline:
User message → Intent Classification → RAG Retrieval → LLM Generation → Response
"""

import logging
from datetime import datetime

from fastapi import APIRouter, HTTPException

from app.core.llm_router import get_llm_router, Intent
from app.core.prompts import POLICY_QA_PROMPT, CHECKLIST_PROMPT, RFE_ANALYSIS_PROMPT
from app.services.rag_service import get_rag_service
from app.schemas.schemas import ChatRequest, ChatResponse
from app.utils.disclaimer import inject_disclaimer, check_confidence, CASE_SPECIFIC_REDIRECT

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint.

    Flow:
    1. Classify intent (Gemini Flash)
    2. Retrieve relevant context (ChromaDB)
    3. Build prompt with context
    4. Route to optimal LLM
    5. Inject disclaimers
    6. Return response
    """
    try:
        llm_router = get_llm_router()
        rag_service = get_rag_service()

        # --- Step 1: Classify Intent ---
        classified = await llm_router.classify_intent(request.message)
        logger.info(
            f"Intent: {classified.intent} | Confidence: {classified.confidence} | "
            f"Visa: {classified.visa_type} | Topic: {classified.sub_topic}"
        )

        # --- Step 2: Handle case-specific redirects ---
        if classified.intent == Intent.CASE_SPECIFIC:
            return ChatResponse(
                response=CASE_SPECIFIC_REDIRECT,
                intent=classified.intent.value,
                confidence=classified.confidence,
                model_used="system",
                sources=[],
                requires_lawyer=True,
            )

        # --- Step 3: Retrieve context from knowledge base ---
        retrieved_docs = rag_service.retrieve(
            query=request.message,
            n_results=5,
            collection_name="uscis_policy",
        )
        context, sources = rag_service.format_context(retrieved_docs)

        # --- Step 4: Build prompt ---
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
        else:
            system_prompt = POLICY_QA_PROMPT.format(
                context=context,
                question=request.message,
                chat_history=chat_history_str or "No prior history.",
            )

        # --- Step 5: Route to LLM ---
        llm_response = await llm_router.route_and_respond(
            user_message=request.message,
            system_prompt=system_prompt,
            intent=classified.intent,
        )

        # --- Step 6: Post-process ---
        response_text = llm_response.content

        # Add confidence warning if needed
        confidence_warning = check_confidence(classified.confidence)
        if confidence_warning:
            response_text = confidence_warning + "\n\n" + response_text

        # Inject disclaimer based on intent
        disclaimer_type = {
            Intent.RFE_HELP: "rfe",
            Intent.TIMELINE: "timeline",
        }.get(classified.intent, "standard")
        response_text = inject_disclaimer(response_text, disclaimer_type)

        return ChatResponse(
            response=response_text,
            intent=classified.intent.value,
            confidence=classified.confidence,
            model_used=llm_response.model_used,
            sources=sources,
            requires_lawyer=classified.requires_lawyer,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail="An error occurred processing your request. Please try again.",
        )


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    rag_service = get_rag_service()
    doc_count = rag_service.policy_collection.count()
    return {
        "status": "healthy",
        "knowledge_base_documents": doc_count,
        "timestamp": datetime.utcnow().isoformat(),
    }
