"""Document checklist generation service."""

from pydantic import BaseModel, Field

from app.core.llm_router import Intent
from app.core.prompts import CHECKLIST_PROMPT
from app.schemas.schemas import (
    ChecklistCategory,
    ChecklistItem,
    ChecklistRequest,
    ChecklistResponse,
)
from app.services.llm_json_service import generate_structured
from app.services.rag_service import get_rag_service


class _ChecklistItemRaw(BaseModel):
    document: str
    required: bool = True
    description: str = ""
    tips: str = ""


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
    disclaimer: str = ""


class ChecklistService:
    async def generate(self, request: ChecklistRequest) -> ChecklistResponse:
        rag = get_rag_service()
        query = f"{request.visa_type.value} document checklist {request.details}"
        retrieved = rag.retrieve(query, n_results=5, collection_name="uscis_policy")
        context, _ = rag.format_context(retrieved)

        prompt = CHECKLIST_PROMPT.format(
            visa_type=request.visa_type.value,
            details=request.details or "No additional details provided.",
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
            visa_type=raw.visa_type,
            form_number=raw.form_number,
            checklist=categories,
            filing_fee=raw.filing_fee,
            estimated_prep_time=raw.estimated_prep_time,
            common_mistakes=raw.common_mistakes,
            disclaimer=disclaimer,
        )
