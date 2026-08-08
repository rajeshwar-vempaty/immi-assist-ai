"""Case profile service — persist and format immigration case context."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy.orm import Session

from app.models.models import User, UserCaseProfile
from app.schemas.schemas import CaseProfileResponse, CaseProfileUpdate


def _empty_response() -> CaseProfileResponse:
    return CaseProfileResponse()


def to_response(profile: UserCaseProfile | None) -> CaseProfileResponse:
    if profile is None:
        return _empty_response()
    return CaseProfileResponse(
        visa_type=profile.visa_type,
        form_number=profile.form_number,
        service_center=profile.service_center,
        office_code=profile.office_code,
        priority_date=profile.priority_date,
        country_of_chargeability=profile.country_of_chargeability,
        has_dependents=bool(profile.has_dependents),
        premium_processing=bool(profile.premium_processing),
        employer_name=profile.employer_name,
        notes=profile.notes or "",
        updated_at=profile.updated_at,
    )


def get_profile(db: Session, user: User) -> CaseProfileResponse:
    profile = (
        db.query(UserCaseProfile)
        .filter(UserCaseProfile.user_id == user.id)
        .one_or_none()
    )
    return to_response(profile)


def upsert_profile(db: Session, user: User, body: CaseProfileUpdate) -> CaseProfileResponse:
    profile = (
        db.query(UserCaseProfile)
        .filter(UserCaseProfile.user_id == user.id)
        .one_or_none()
    )
    if profile is None:
        profile = UserCaseProfile(user_id=user.id)
        db.add(profile)

    data = body.model_dump(exclude_unset=True)
    for key, value in data.items():
        if key == "notes" and value is None:
            value = ""
        setattr(profile, key, value)
    profile.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(profile)
    return to_response(profile)


def format_profile_context(profile: CaseProfileResponse | None) -> str:
    """Plain-text block injected into checklist/RFE/chat prompts."""
    if profile is None:
        return "No saved case profile."
    lines = []
    mapping = [
        ("Visa / petition type", profile.visa_type),
        ("Primary form", profile.form_number),
        ("Service center / office", profile.service_center or profile.office_code),
        ("Priority date", profile.priority_date),
        ("Country of chargeability", profile.country_of_chargeability),
        ("Has dependents", "yes" if profile.has_dependents else "no"),
        ("Premium processing", "yes" if profile.premium_processing else "no"),
        ("Employer", profile.employer_name),
        ("Notes", profile.notes),
    ]
    # Only emit boolean flags when other profile fields exist (avoid noise for empty profiles).
    has_core = any(
        [
            profile.visa_type,
            profile.form_number,
            profile.service_center,
            profile.office_code,
            profile.priority_date,
            profile.country_of_chargeability,
            profile.employer_name,
            profile.notes,
        ]
    )
    for label, value in mapping:
        if label in ("Has dependents", "Premium processing"):
            if not has_core:
                continue
            lines.append(f"- {label}: {value}")
            continue
        if value in (None, ""):
            continue
        lines.append(f"- {label}: {value}")
    return "\n".join(lines) if lines else "No saved case profile."
