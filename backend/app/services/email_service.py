"""Welcome email delivery for new registrations."""

from __future__ import annotations

import logging
import smtplib
from email.message import EmailMessage

from app.core.config import get_settings

logger = logging.getLogger(__name__)

WELCOME_SUBJECT = "Welcome to ImmiAssist — what this tool does for you"

WELCOME_BODY = """Hi {name},

Thanks for creating an ImmiAssist account with {email}.

Here is a short summary of what this tool helps you do:

• Ask clear questions about U.S. immigration topics (visas, forms, timelines, RFEs)
• Get answers grounded in official USCIS policy and processing-time data when available
• Build document checklists for common filing types
• Estimate typical processing timelines (informational ranges, not case status)
• Organize an RFE response outline with suggested evidence themes
• Save your own AI provider API keys securely and choose which model to use in chat
• Keep your conversation history private to your account

Important: ImmiAssist is an informational assistant — not a lawyer and not a substitute
for licensed immigration counsel. Always verify critical decisions with official USCIS
sources or a qualified attorney.

Get started: open the app, add an API key under Settings (if needed), and ask your first question.

— The ImmiAssist team
"""


def send_welcome_email(*, to_email: str, name: str) -> dict:
    """Send (or log) the product summary welcome email. Never raises to callers."""
    settings = get_settings()
    body = WELCOME_BODY.format(name=name or "there", email=to_email)
    if not settings.smtp_host or settings.email_log_only:
        logger.info(
            "Welcome email (log-only) to=%s subject=%s\n%s",
            to_email,
            WELCOME_SUBJECT,
            body,
        )
        return {"sent": False, "mode": "log_only"}

    msg = EmailMessage()
    msg["Subject"] = WELCOME_SUBJECT
    msg["From"] = settings.smtp_from_email
    msg["To"] = to_email
    msg.set_content(body)

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
            if settings.smtp_use_tls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password)
            smtp.send_message(msg)
        logger.info("Welcome email sent to=%s", to_email)
        return {"sent": True, "mode": "smtp"}
    except Exception:
        logger.exception("Failed to send welcome email to=%s", to_email)
        return {"sent": False, "mode": "error"}
