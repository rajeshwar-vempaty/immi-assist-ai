"""RFE analysis service."""

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.llm_router import Intent
from app.core.prompts import RFE_ANALYSIS_PROMPT
from app.models.models import User
from app.schemas.schemas import RFEAnalysis, RFEPoint, RFERequest, SourceRef
from app.services import case_profile_service as profiles
from app.services.llm_json_service import generate_structured
from app.services.rag_service import get_rag_service

RFE_JSON_PROMPT_SUFFIX = """

Respond with ONLY a JSON object:
{
    "summary": "<plain English summary>",
    "deadline_info": "<deadline and implications>",
    "risk_level": "routine | moderate | serious",
    "points": [{
        "issue": "<issue title>",
        "what_uscis_wants": "<plain English ask>",
        "evidence_suggestions": ["<suggestion>"],
        "severity": "routine | moderate | serious",
        "policy_anchor": "<policy cue if known>"
    }],
    "response_outline": ["<step 1>", "<step 2>"],
    "next_steps": ["<action 1>", "<action 2>"],
    "disclaimer": "This analysis is for informational purposes only. Work with a licensed immigration attorney."
}
"""


class _RFEPoint(BaseModel):
    issue: str
    what_uscis_wants: str = ""
    evidence_suggestions: list[str] = Field(default_factory=list)
    severity: str = "moderate"
    policy_anchor: str = ""


class _RFELLMResponse(BaseModel):
    summary: str
    deadline_info: str = ""
    risk_level: str = "moderate"
    points: list[_RFEPoint] = Field(default_factory=list)
    response_outline: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class RFEService:
    def __init__(self, db: Session | None = None, user: User | None = None):
        self.db = db
        self.user = user

    async def analyze(self, request: RFERequest) -> RFEAnalysis:
        profile = None
        profile_applied = False
        if request.use_case_profile and self.db is not None and self.user is not None:
            profile = profiles.get_profile(self.db, self.user)
            profile_applied = True

        petition = (
            request.petition_type.value
            if request.petition_type
            else (profile.visa_type if profile and profile.visa_type else "Unknown")
        )
        case_block = profiles.format_profile_context(profile) if profile else "No saved case profile."
        extra = request.additional_context or ""
        if profile and profile.notes:
            extra = (extra + "\n" + profile.notes).strip()

        rag = get_rag_service()
        query = f"{petition} RFE {request.rfe_text[:400]}"
        retrieved = rag.retrieve(query, n_results=8, collection_name="uscis_policy")
        context, sources = rag.format_context(retrieved)

        prompt = RFE_ANALYSIS_PROMPT.format(
            rfe_text=request.rfe_text,
            petition_type=petition,
            additional_context=extra or "None provided.",
            case_profile=case_block,
            context=context,
        ) + RFE_JSON_PROMPT_SUFFIX

        raw = await generate_structured(
            user_message="Analyze this RFE",
            system_prompt=prompt,
            intent=Intent.RFE_HELP,
            response_model=_RFELLMResponse,
        )

        points = [
            RFEPoint(
                issue=p.issue,
                what_uscis_wants=p.what_uscis_wants,
                evidence_suggestions=p.evidence_suggestions,
                severity=p.severity or "moderate",
                policy_anchor=p.policy_anchor,
            )
            for p in raw.points
        ]

        return RFEAnalysis(
            summary=raw.summary,
            deadline_info=raw.deadline_info,
            risk_level=raw.risk_level,
            points=points,
            response_outline=raw.response_outline,
            next_steps=raw.next_steps,
            sources=[SourceRef(**s) if isinstance(s, dict) else s for s in sources],
            profile_applied=profile_applied,
            disclaimer=raw.disclaimer
            or "This analysis is for informational purposes only. Work with a licensed immigration attorney.",
        )
