"""Monitoring and observability setup."""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


def init_sentry(dsn: str | None = None, environment: str = "development"):
    """Initialize Sentry for error tracking."""
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_dsn = dsn or os.getenv("SENTRY_DSN")
        if not sentry_dsn:
            logger.warning("Sentry DSN not provided, skipping initialization")
            return

        sentry_sdk.init(
            dsn=sentry_dsn,
            environment=environment,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
            ],
            traces_sample_rate=0.1 if environment == "production" else 1.0,
            profiles_sample_rate=0.1 if environment == "production" else 1.0,
        )

        logger.info(f"Sentry initialized for {environment} environment")

    except ImportError:
        logger.warning("sentry-sdk not installed, skipping Sentry initialization")
    except Exception as e:
        logger.error(f"Failed to initialize Sentry: {e}")


def capture_exception(error: Exception):
    """Capture exception to Sentry if available."""
    try:
        import sentry_sdk

        sentry_sdk.capture_exception(error)
    except ImportError:
        pass
