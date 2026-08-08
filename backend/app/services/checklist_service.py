"""Document checklist generation service."""

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.llm_router import Intent
from app.core.prompts import CHECKLIST_PROMPT
from app.models.models import User
from app.schemas.schemas import (
    ChecklistCategory,
    ChecklistItem,
    ChecklistRequest,
    ChecklistResponse,
    SourceRef,
)
from app.services import case_profile_service as profiles
from app.services.llm_json_service import generate_structured
from app.services.rag_service import get_rag_service


class _ChecklistItemRaw(BaseModel):
    document: str
    required: bool = True
    description: str = ""
    tips: str = ""
    why_needed: str = ""
    source_hint: str = ""


class _ChecklistCategoryRaw(BaseModel):
    category: str
    items: list[_ChecklistItemRaw] = Field(default_factory=list)


class _ChecklistLLMResponse(BaseModel):
    visa_type: str
    form_number: str = ""
    checklist: list[_ChecklistCategoryRaw] = Field(default_factory=list)
    filing_fee: str = "See USCIS fee schedule"
    estimated_prep_time: str = "2-4 weeks"
    common_mistakes: list[str] = Field(default_factory=list)
    missing_if_dependents: list[str] = Field(default_factory=list)
    filing_methods: list[str] = Field(default_factory=list)
    disclaimer: str = ""


class ChecklistService:
    def __init__(self, db: Session | None = None, user: User | None = None):
        self.db = db
        self.user = user

    async def generate(self, request: ChecklistRequest) -> ChecklistResponse:
        profile = None
        profile_applied = False
        if request.use_case_profile and self.db is not None and self.user is not None:
            profile = profiles.get_profile(self.db, self.user)
            profile_applied = True

        has_dependents = request.has_dependents or bool(profile and profile.has_dependents)
        premium = request.is_premium_processing or bool(profile and profile.premium_processing)
        form_number = request.form_number or (profile.form_number if profile else "") or ""
        service_center = request.service_center or (profile.service_center if profile else "") or ""
        employer = request.employer_name or (profile.employer_name if profile else "") or ""
        case_block = profiles.format_profile_context(profile) if profile else "No saved case profile."

        rag = get_rag_service()
        query = (
            f"{request.visa_type.value} {form_number} document checklist filing requirements "
            f"{request.details} {employer}"
        ).strip()
        retrieved = rag.retrieve(query, n_results=8, collection_name="uscis_policy")
        context, sources = rag.format_context(retrieved)

        prompt = CHECKLIST_PROMPT.format(
            visa_type=request.visa_type.value,
            form_number=form_number or "Unknown",
            service_center=service_center or "Unknown",
            employer_name=employer or "Not provided",
            has_dependents="yes" if has_dependents else "no",
            premium_processing="yes" if premium else "no",
            details=request.details or "No additional details provided.",
            case_profile=case_block,
            context=context,
        )

        raw = await generate_structured(
            user_message=f"Generate checklist for {request.visa_type.value}",
            system_prompt=prompt,
            intent=Intent.CHECKLIST,
            response_model=_ChecklistLLMResponse,
        )

        categories = [
            ChecklistCategory(
                category=cat.category,
                items=[
                    ChecklistItem(
                        document=item.document,
                        required=item.required,
                        description=item.description,
                        tips=item.tips,
                        why_needed=item.why_needed,
                        source_hint=item.source_hint,
                    )
                    for item in cat.items
                ],
            )
            for cat in raw.checklist
        ]

        disclaimer = raw.disclaimer or (
            "This checklist is for informational purposes only. Consult an immigration attorney."
        )
        return ChecklistResponse(
            visa_type=raw.visa_type or request.visa_type.value,
            form_number=raw.form_number or form_number,
            checklist=categories,
            filing_fee=raw.filing_fee,
            estimated_prep_time=raw.estimated_prep_time,
            common_mistakes=raw.common_mistakes,
            missing_if_dependents=raw.missing_if_dependents,
            filing_methods=raw.filing_methods or ["online", "mail"],
            sources=[SourceRef(**s) if isinstance(s, dict) else s for s in sources],
            profile_applied=profile_applied,
            disclaimer=disclaimer,
        )
