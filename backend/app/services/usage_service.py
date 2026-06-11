"""Usage tracking and rate limit enforcement."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.deps import AuthContext
from app.core.exceptions import RateLimitExceeded
from app.models.models import UsageEvent


def get_daily_limit(tier: str) -> int:
    settings = get_settings()
    if tier == "starter":
        return settings.starter_tier_daily_limit
    return settings.free_tier_daily_limit


def count_usage_last_24h(db: Session, auth: AuthContext) -> int:
    """Count LLM usage events in the last 24 hours."""
    since = datetime.utcnow() - timedelta(hours=24)
    query = db.query(UsageEvent).filter(UsageEvent.created_at >= since)

    if auth.user:
        query = query.filter(UsageEvent.user_id == auth.user.id)
    else:
        query = query.filter(
            UsageEvent.anonymous_session_id == auth.anonymous_session_id
        )

    return query.count()


def check_rate_limit(db: Session, auth: AuthContext) -> None:
    """Raise RateLimitExceeded if daily limit reached."""
    limit = get_daily_limit(auth.tier)
    count = count_usage_last_24h(db, auth)
    if count >= limit:
        raise RateLimitExceeded(
            f"Daily limit of {limit} requests reached. Register for an API key to increase limits."
        )


def record_usage(
    db: Session,
    auth: AuthContext,
    endpoint: str,
    tokens_estimate: int = 0,
) -> None:
    """Record a usage event."""
    event = UsageEvent(
        user_id=auth.user.id if auth.user else None,
        anonymous_session_id=auth.anonymous_session_id if not auth.user else None,
        endpoint=endpoint,
        tokens_estimate=tokens_estimate,
    )
    db.add(event)
    db.commit()
