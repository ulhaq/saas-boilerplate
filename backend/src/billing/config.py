"""Billing settings, read from the environment like the platform's
(`STRIPE_*` and `BILLING_*` variables)."""

from typing import Literal, Self

from pydantic import SecretStr, model_validator

from src.platform.core.config import EnvSettings


class BillingSettings(EnvSettings):
    # Read from APP_ENV, for the production checks below.
    app_env: Literal["local", "development", "staging", "production"] = "local"

    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    # Per attempt; failed attempts are retried (with idempotency keys).
    stripe_timeout_seconds: float = 10
    stripe_max_network_retries: int = 2
    billing_success_url: str = "http://localhost:5173/billing/success"
    billing_cancel_url: str = "http://localhost:5173/billing/cancel"
    billing_portal_return_url: str = "http://localhost:5173/settings/billing"
    billing_automatic_tax: bool = False
    billing_trial_period_days: int = 7
    billing_cleanup_interval_seconds: int = 24 * 60 * 60
    billing_trial_reminder_delay_days: int = 3
    billing_trial_reminder_interval_seconds: int = 24 * 60 * 60
    billing_customer_sync_interval_seconds: int = 60

    @model_validator(mode="after")
    def validate_billing_urls(self) -> Self:
        if self.app_env == "production":
            for field_name in (
                "billing_success_url",
                "billing_cancel_url",
                "billing_portal_return_url",
            ):
                url = getattr(self, field_name)
                if "localhost" in url or "127.0.0.1" in url:
                    raise ValueError(
                        f"{field_name} must not point to localhost in production",
                    )
        return self

    @model_validator(mode="after")
    def validate_production_credentials(self) -> Self:
        if self.app_env not in ("local", "development"):
            if not self.stripe_secret_key.get_secret_value():
                raise ValueError(
                    "STRIPE_SECRET_KEY must be set in non-local environments",
                )
            if not self.stripe_webhook_secret.get_secret_value():
                raise ValueError(
                    "STRIPE_WEBHOOK_SECRET must be set in non-local environments",
                )
        return self


billing_settings = BillingSettings()
