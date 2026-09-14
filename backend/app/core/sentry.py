"""Optional Sentry wiring. No-op when SENTRY_DSN is empty."""

from __future__ import annotations

import logging

from app.core.config import settings

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        if (settings.environment or "").strip().lower() == "production":
            logger.warning(
                "ENVIRONMENT=production but SENTRY_DSN is empty — errors will only hit logs."
            )
        return
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.error("SENTRY_DSN is set but sentry-sdk is not installed.")
        return

    traces = settings.sentry_traces_sample_rate
    if (settings.environment or "").strip().lower() == "production" and traces <= 0:
        traces = 0.1

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.environment,
        traces_sample_rate=traces,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        send_default_pii=False,
    )
    logger.info("Sentry error reporting enabled (%s).", settings.environment)
