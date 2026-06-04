"""RFE analysis service."""

from pydantic import BaseModel, Field

from app.core.llm_router import Intent
from app.core.prompts import RFE_ANALYSIS_PROMPT
from app.schemas.schemas import RFEAnalysis, RFERequest
from app.services.llm_json_service import generate_structured
from app.services.rag_service import get_rag_service

RFE_JSON_PROMPT_SUFFIX = """

Respond with ONLY a JSON object:
{
    "summary": "<plain English summary>",
    "deadline_info": "<deadline and implications>",
    "risk_level": "routine | moderate | serious",
    "points": [{"issue": "<issue>", "evidence_suggestions": ["<suggestion>"]}],
    "response_outline": ["<step 1>", "<step 2>"],
    "next_steps": ["<action 1>", "<action 2>"],
    "disclaimer": "This analysis is for informational purposes only. Work with a licensed immigration attorney."
}
"""


class _RFEPoint(BaseModel):
    issue: str
    evidence_suggestions: list[str] = Field(default_factory=list)


class _RFELLMResponse(BaseModel):
    summary: str
    deadline_info: str = ""
    risk_level: str = "moderate"
    points: list[_RFEPoint] = Field(default_factory=list)
    response_outline: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class RFEService:
    async def analyze(self, request: RFERequest) -> RFEAnalysis:
        rag = get_rag_service()
        retrieved = rag.retrieve(
            request.rfe_text[:500],
            n_results=5,
            collection_name="uscis_policy",
        )
        context, _ = rag.format_context(retrieved)

        prompt = RFE_ANALYSIS_PROMPT.format(
            rfe_text=request.rfe_text,
            petition_type=request.petition_type.value if request.petition_type else "Unknown",
            context=context,
        ) + RFE_JSON_PROMPT_SUFFIX

        raw = await generate_structured(
            user_message="Analyze this RFE",
            system_prompt=prompt,
            intent=Intent.RFE_HELP,
            response_model=_RFELLMResponse,
        )

        points = [
            {
                "issue": p.issue,
                "evidence_suggestions": p.evidence_suggestions,
            }
            for p in raw.points
        ]

        return RFEAnalysis(
            summary=raw.summary,
            deadline_info=raw.deadline_info,
            risk_level=raw.risk_level,
            points=points,
            response_outline=raw.response_outline,
            next_steps=raw.next_steps,
            disclaimer=raw.disclaimer,
        )
