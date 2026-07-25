"""Processing timeline estimation — official USCIS times + LLM explanation."""

from datetime import date, timedelta

from pydantic import BaseModel, Field

from app.core.llm_router import Intent
from app.core.prompts import TIMELINE_PROMPT
from app.schemas.schemas import TimelineRequest, TimelineResponse
from app.services.llm_json_service import generate_structured
from app.services.processing_time_resolver import format_official_block, lookup_official_time
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
        official = await lookup_official_time(
            form_type=request.form_type,
            category=request.category,
            service_center=request.service_center.value if request.service_center else None,
            message=f"{request.form_type} {request.category or ''}",
        )
        official_block = format_official_block(official) if official else ""

        rag = get_rag_service()
        query = f"{request.form_type} processing time {request.service_center or ''} {request.category or ''}"
        retrieved = rag.retrieve(query, n_results=5, collection_name="processing_times")
        processing_context, _ = rag.format_context(retrieved)
        if official_block:
            processing_context = f"{official_block}\n\n---\nSupporting RAG notes:\n{processing_context}"
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

        if official and official.get("months") is not None:
            months = float(official["months"])
            # USCIS publishes a single "80% within" figure — expose as max, with a soft lower bound.
            processing_range_months = {
                "min": round(max(months * 0.55, 0.5), 1),
                "max": months,
            }
            data_source = official.get("source", "snapshot")
            data_as_of = official.get("as_of") or official.get("publication_date")
            uscis_url = official.get("uscis_url")
            official_months = months
            if request.filing_date:
                try:
                    filed = date.fromisoformat(request.filing_date)
                    earliest = filed + timedelta(days=int(processing_range_months["min"] * 30))
                    latest = filed + timedelta(days=int(months * 30))
                    estimated_completion = {
                        "earliest": earliest.isoformat(),
                        "latest": latest.isoformat(),
                    }
                except ValueError:
                    estimated_completion = raw.estimated_completion
            else:
                estimated_completion = raw.estimated_completion
            status_explanation = raw.status_explanation or (
                f"USCIS reports that 80% of cases in this category finish within {months} months "
                f"({data_source} data{f', as of {data_as_of}' if data_as_of else ''})."
            )
        else:
            proc_range = raw.current_processing_range
            processing_range_months = {
                "min": proc_range.get("min_months", proc_range.get("min", 0)),
                "max": proc_range.get("max_months", proc_range.get("max", 0)),
            }
            estimated_completion = raw.estimated_completion
            status_explanation = raw.status_explanation
            data_source = "llm"
            data_as_of = None
            uscis_url = None
            official_months = None

        disclaimer = raw.disclaimer or inject_disclaimer("", "timeline").strip()
        return TimelineResponse(
            form_type=raw.form_type or request.form_type,
            service_center=raw.service_center
            or (request.service_center.value if request.service_center else None),
            processing_range_months=processing_range_months,
            estimated_completion=estimated_completion,
            case_status=raw.case_status,
            status_explanation=status_explanation,
            options_if_delayed=raw.options_if_delayed,
            disclaimer=disclaimer,
            data_source=data_source,
            data_as_of=data_as_of,
            official_months=official_months,
            uscis_url=uscis_url,
        )
