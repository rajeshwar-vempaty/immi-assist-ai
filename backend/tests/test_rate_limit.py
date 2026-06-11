"""Rate limit tests."""

from app.core.deps import AuthContext
from app.models.models import UsageEvent
from app.services.usage_service import check_rate_limit, count_usage_last_24h, get_daily_limit


def test_daily_limit_free_tier():
    assert get_daily_limit("free") >= 1


def test_rate_limit_not_exceeded(db_session):
    auth = AuthContext(user=None, anonymous_session_id="test-session", api_key_id=None)
    check_rate_limit(db_session, auth)


def test_rate_limit_exceeded(db_session):
    from app.core.config import get_settings

    settings = get_settings()
    auth = AuthContext(user=None, anonymous_session_id="limit-session", api_key_id=None)

    for _ in range(settings.free_tier_daily_limit):
        db_session.add(
            UsageEvent(
                anonymous_session_id="limit-session",
                endpoint="/chat",
            )
        )
    db_session.commit()

    assert count_usage_last_24h(db_session, auth) >= settings.free_tier_daily_limit

    from app.core.exceptions import RateLimitExceeded
    import pytest

    with pytest.raises(RateLimitExceeded):
        check_rate_limit(db_session, auth)
