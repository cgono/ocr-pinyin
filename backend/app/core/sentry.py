import logging
import os

logger = logging.getLogger(__name__)


def init_sentry() -> None:
    """Initialize Sentry if configured, without affecting app startup on failure."""
    dsn = os.getenv("SENTRY_DSN", "").strip()
    if not dsn:
        return

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration

        traces_sample_rate = float(os.getenv("SENTRY_TRACES_SAMPLE_RATE", "1.0"))
        sentry_sdk.init(
            dsn=dsn,
            environment=os.getenv("APP_ENV", "development"),
            release=os.getenv("APP_VERSION", "0.1.0"),
            traces_sample_rate=traces_sample_rate,
            integrations=[
                StarletteIntegration(transaction_style="endpoint"),
                FastApiIntegration(),
            ],
            send_default_pii=False,
        )
        logger.info("Sentry initialized (env=%s)", os.getenv("APP_ENV", "development"))
    except Exception:
        logger.warning("Sentry initialization failed; monitoring disabled.", exc_info=True)
