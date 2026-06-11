"""Processing timeline estimation service."""

from pydantic import BaseModel, Field

from app.core.llm_router import Intent
from app.core.prompts import TIMELINE_PROMPT
from app.schemas.schemas import TimelineRequest, TimelineResponse
from app.services.llm_json_service import generate_structured
from app.services.rag_service import get_rag_service
from app.utils.disclaimer import inject_disclaimer


class _TimelineLLMResponse(BaseModel):
    form_type: str
    service_center: str | None = None
    current_processing_range: dict = Field(default_factory=dict)
    estimated_completion: dict = Field(default_factory=dict)
    case_status: str = "NORMAL"
    status_explanation: str = ""
    options_if_delayed: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class TimelineService:
    async def estimate(self, request: TimelineRequest) -> TimelineResponse:
        rag = get_rag_service()
        query = f"{request.form_type} processing time {request.service_center or ''} {request.category or ''}"
        retrieved = rag.retrieve(query, n_results=5, collection_name="processing_times")
        processing_context, _ = rag.format_context(retrieved)
        policy_context, _ = rag.format_context(
            rag.retrieve(request.form_type, n_results=2, collection_name="uscis_policy")
        )

        prompt = TIMELINE_PROMPT.format(
            form_type=request.form_type,
            service_center=request.service_center.value if request.service_center else "Any",
            filing_date=request.filing_date or "Not provided",
            category=request.category or "General",
            processing_data=processing_context,
            context=policy_context,
        )

        raw = await generate_structured(
            user_message=f"Estimate timeline for {request.form_type}",
            system_prompt=prompt,
            intent=Intent.TIMELINE,
            response_model=_TimelineLLMResponse,
        )

        proc_range = raw.current_processing_range
        processing_range_months = {
            "min": proc_range.get("min_months", proc_range.get("min", 0)),
            "max": proc_range.get("max_months", proc_range.get("max", 0)),
        }

        disclaimer = raw.disclaimer or inject_disclaimer("", "timeline").strip()
        return TimelineResponse(
            form_type=raw.form_type,
            service_center=raw.service_center,
            processing_range_months=processing_range_months,
            estimated_completion=raw.estimated_completion,
            case_status=raw.case_status,
            status_explanation=raw.status_explanation,
            options_if_delayed=raw.options_if_delayed,
            disclaimer=disclaimer,
        )
