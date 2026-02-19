"""
Disclaimer & safety utilities.

Every response MUST include appropriate disclaimers.
"""

STANDARD_DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Disclaimer:** This is informational guidance only and does not constitute legal advice. "
    "Immigration law is complex and individual cases vary significantly. "
    "Please consult a licensed immigration attorney for advice specific to your situation."
)

RFE_DISCLAIMER = (
    "\n\n---\n"
    "⚠️ **Important:** This RFE analysis is for informational purposes only. "
    "An RFE response is a critical legal document that directly impacts your immigration case. "
    "Please work with a licensed immigration attorney to prepare your official response. "
    "Do not submit any response to USCIS based solely on this analysis."
)

TIMELINE_DISCLAIMER = (
    "Processing times are estimates based on publicly available USCIS data and may change. "
    "This is not a guarantee of when your case will be processed. "
    "Check uscis.gov/processing-times for the most current data."
)

CASE_SPECIFIC_REDIRECT = (
    "I understand you're asking about your specific case. While I can provide general information "
    "about immigration processes, I'm not able to give advice on individual cases — that requires "
    "a licensed immigration attorney who can review your complete file.\n\n"
    "Here's what I **can** help with:\n"
    "• General information about your visa/petition type\n"
    "• Document checklists and filing requirements\n"
    "• Processing time estimates\n"
    "• Understanding RFE notices\n\n"
    "Would you like help with any of these?"
)


def inject_disclaimer(response: str, disclaimer_type: str = "standard") -> str:
    """Append the appropriate disclaimer to a response."""
    disclaimers = {
        "standard": STANDARD_DISCLAIMER,
        "rfe": RFE_DISCLAIMER,
        "timeline": TIMELINE_DISCLAIMER,
        "case_specific": CASE_SPECIFIC_REDIRECT,
    }
    disclaimer = disclaimers.get(disclaimer_type, STANDARD_DISCLAIMER)

    # Don't double-add disclaimers
    if "⚠️" in response and "Disclaimer" in response:
        return response

    return response + disclaimer


def check_confidence(confidence: float) -> str | None:
    """Return a low-confidence warning if needed."""
    if confidence < 0.5:
        return (
            "⚠️ I'm not very confident in this answer. The information may not be fully accurate. "
            "I strongly recommend verifying with an immigration attorney or directly on uscis.gov."
        )
    elif confidence < 0.7:
        return (
            "ℹ️ Note: This answer is based on general immigration guidance. "
            "For your specific situation, please verify with an attorney."
        )
    return None
