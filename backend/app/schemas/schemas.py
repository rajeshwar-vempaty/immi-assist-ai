"""
API Request/Response schemas.
"""

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


# ----- Enums -----

class VisaType(str, Enum):
    H1B = "H1B"
    H4 = "H4"
    H4_EAD = "H4_EAD"
    L1A = "L1A"
    L1B = "L1B"
    O1 = "O1"
    EB1 = "EB1"
    EB2 = "EB2"
    EB3 = "EB3"
    EB2_NIW = "EB2_NIW"
    F1 = "F1"
    F1_OPT = "F1_OPT"
    F1_STEM_OPT = "F1_STEM_OPT"
    I485 = "I-485"
    I130 = "I-130"
    I140 = "I-140"
    K1 = "K1"
    TN = "TN"
    OTHER = "OTHER"


class ServiceCenter(str, Enum):
    CALIFORNIA = "California Service Center"
    NEBRASKA = "Nebraska Service Center"
    TEXAS = "Texas Service Center"
    VERMONT = "Vermont Service Center"
    POTOMAC = "Potomac Service Center"
    NBC = "National Benefits Center"


# ----- Chat -----

class ChatMessage(BaseModel):
    role: str = Field(..., pattern="^(user|assistant)$")
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=5000)
    chat_history: list[ChatMessage] = Field(default_factory=list)
    conversation_id: Optional[str] = Field(None, description="Existing conversation ID")
    session_id: Optional[str] = Field(None, description="Deprecated alias for conversation_id")
    provider: Optional[str] = Field(None, description="Selected AI provider")
    model: Optional[str] = Field(None, description="Selected model id")
    language: str = Field(default="en", description="Response language code")


class SourceRef(BaseModel):
    label: str
    url: str = ""
    excerpt: str = ""


class ChatResponse(BaseModel):
    response: str
    intent: str
    confidence: float
    model_used: str
    provider: Optional[str] = None
    sources: list[SourceRef] = Field(default_factory=list)
    requires_lawyer: bool = False
    conversation_id: Optional[str] = None
    session_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ----- Case Profile -----

class CaseProfileUpdate(BaseModel):
    visa_type: Optional[str] = Field(None, max_length=32)
    form_number: Optional[str] = Field(None, max_length=32)
    service_center: Optional[str] = Field(None, max_length=128)
    office_code: Optional[str] = Field(None, max_length=64)
    priority_date: Optional[str] = Field(None, max_length=32)
    country_of_chargeability: Optional[str] = Field(None, max_length=128)
    has_dependents: Optional[bool] = None
    premium_processing: Optional[bool] = None
    employer_name: Optional[str] = Field(None, max_length=255)
    notes: Optional[str] = Field(None, max_length=4000)


class CaseProfileResponse(BaseModel):
    visa_type: Optional[str] = None
    form_number: Optional[str] = None
    service_center: Optional[str] = None
    office_code: Optional[str] = None
    priority_date: Optional[str] = None
    country_of_chargeability: Optional[str] = None
    has_dependents: bool = False
    premium_processing: bool = False
    employer_name: Optional[str] = None
    notes: str = ""
    updated_at: Optional[datetime] = None


# ----- Document Checklist -----

class ChecklistRequest(BaseModel):
    visa_type: VisaType
    details: str = Field(default="", max_length=2000, description="Additional context about your situation")
    has_dependents: bool = False
    is_premium_processing: bool = False
    use_case_profile: bool = True
    form_number: Optional[str] = Field(None, max_length=32)
    service_center: Optional[str] = Field(None, max_length=128)
    employer_name: Optional[str] = Field(None, max_length=255)


class ChecklistItem(BaseModel):
    document: str
    required: bool
    description: str
    tips: str = ""
    why_needed: str = ""
    source_hint: str = ""


class ChecklistCategory(BaseModel):
    category: str
    items: list[ChecklistItem]


class ChecklistResponse(BaseModel):
    visa_type: str
    form_number: str
    checklist: list[ChecklistCategory]
    filing_fee: str
    estimated_prep_time: str
    common_mistakes: list[str]
    missing_if_dependents: list[str] = Field(default_factory=list)
    filing_methods: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    profile_applied: bool = False
    disclaimer: str


# ----- Timeline -----

class TimelineRequest(BaseModel):
    form_type: str = Field(..., description="e.g., I-129, I-140, I-485")
    service_center: Optional[ServiceCenter] = None
    filing_date: Optional[str] = Field(None, description="Filing date YYYY-MM-DD")
    category: Optional[str] = Field(None, description="e.g., EB2-India, H1B-Extension")


class TimelineResponse(BaseModel):
    form_type: str
    service_center: Optional[str]
    processing_range_months: dict  # {"min": x, "max": y}
    estimated_completion: dict  # {"earliest": date, "latest": date}
    case_status: str  # NORMAL, DELAYED, SIGNIFICANTLY_DELAYED
    status_explanation: str
    options_if_delayed: list[str]
    disclaimer: str
    data_source: Optional[str] = Field(
        None, description="live | snapshot | llm — where the wait-time figure came from"
    )
    data_as_of: Optional[str] = None
    official_months: Optional[float] = Field(
        None, description="USCIS '80% of cases completed within' months when available"
    )
    uscis_url: Optional[str] = None


# ----- RFE Analysis -----

class RFERequest(BaseModel):
    rfe_text: str = Field(..., min_length=10, max_length=20000, description="The RFE notice text")
    petition_type: Optional[VisaType] = None
    additional_context: str = Field(default="", max_length=5000)
    use_case_profile: bool = True


class RFEPoint(BaseModel):
    issue: str
    what_uscis_wants: str = ""
    evidence_suggestions: list[str] = Field(default_factory=list)
    severity: str = "moderate"  # routine | moderate | serious
    policy_anchor: str = ""


class RFEAnalysis(BaseModel):
    summary: str
    deadline_info: str
    risk_level: str  # routine, moderate, serious
    points: list[RFEPoint] = Field(default_factory=list)
    response_outline: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)
    sources: list[SourceRef] = Field(default_factory=list)
    profile_applied: bool = False
    disclaimer: str
