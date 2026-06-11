"""Sentry error tracking integration."""

import logging

from app.core.config import Settings

logger = logging.getLogger(__name__)


def init_sentry(settings: Settings) -> None:
    """Initialize Sentry when SENTRY_DSN is configured."""
    if not settings.sentry_dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        sentry_sdk.init(
            dsn=settings.sentry_dsn,
            environment=settings.app_env,
            release="immi-assist@1.0.0",
            traces_sample_rate=settings.sentry_traces_sample_rate,
            integrations=[
                FastApiIntegration(),
                StarletteIntegration(),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry initialized")
    except Exception as exc:
        logger.warning(f"Sentry initialization failed: {exc}")
