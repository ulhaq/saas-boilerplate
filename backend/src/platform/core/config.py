from typing import Literal, Self

from pydantic import Field, SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_comma_list(value: str) -> list[str]:
    return [v.strip().rstrip("/") for v in value.split(",")]


class EnvSettings(BaseSettings):
    """Shared base for all settings classes: defines where settings are read
    from, nothing else. Product packages extend this with their own namespaced
    settings class (e.g. `ExampleSettings` with `env_prefix="example_"`)."""

    model_config = SettingsConfigDict(
        env_file="./.env", env_file_encoding="utf-8", extra="ignore"
    )


class Settings(EnvSettings):
    app_name: str = "SaaS Boilerplate"
    app_url: str = "http://localhost"
    app_env: Literal["local", "development", "staging", "production"] = "local"
    app_secret: SecretStr = SecretStr("")
    app_debug: bool = False

    # IANA timezone used to render dates in user-facing emails (the calendar day
    # a date lands on depends on the zone). Times are stored in UTC; this only
    # affects display formatting.
    display_timezone: str = "Europe/Copenhagen"

    db_connection: str = ""

    allow_multiple_organizations: bool = True

    auth_enabled: bool = True
    auth_access_token_expiry: int = 15 * 60
    auth_refresh_token_expiry: int = 15 * 24 * 60 * 60
    auth_password_reset_expiry: int = 10 * 60
    email_verification_expiry: int = 60 * 60 * 24
    complete_registration_expiry: int = 30 * 60
    invite_expiry: int = 7 * 24 * 60 * 60

    raw_allow_origins: str = Field(
        default="http://localhost:5173", validation_alias="allow_origins"
    )

    @computed_field
    @property
    def allow_origins(self) -> list[str]:
        return _parse_comma_list(self.raw_allow_origins)

    allow_credentials: bool = True

    email_host: str = ""
    email_user: str = ""
    email_password: str = ""
    email_tls: bool = True
    email_port: int = 587
    email_from_address: str = "noreply@example.org"
    email_from_name: str = "SaaS Boilerplate"

    frontend_url: str = "http://localhost:5173"

    rate_limit_enabled: bool = True

    stripe_secret_key: SecretStr = SecretStr("")
    stripe_webhook_secret: SecretStr = SecretStr("")
    billing_success_url: str = "http://localhost:5173/billing/success"
    billing_cancel_url: str = "http://localhost:5173/billing/cancel"
    billing_portal_return_url: str = "http://localhost:5173/settings/billing"
    billing_automatic_tax: bool = False
    billing_trial_period_days: int = 7
    billing_cleanup_interval_seconds: int = 24 * 60 * 60
    billing_trial_reminder_delay_days: int = 3
    billing_trial_reminder_interval_seconds: int = 24 * 60 * 60

    gdpr_retention_days: int = 30
    gdpr_token_purge_days: int = 7
    gdpr_export_audit_log_limit: int = 500
    gdpr_retention_interval_seconds: int = 24 * 60 * 60

    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30
    db_pool_recycle: int = 1800

    log_format: str = "text"
    log_level: str = "INFO"
    log_exc_info: bool = True
    sqlalchemy_echo: bool = False

    permissions_cache_max_age: int = 60 * 60

    plans_cache_max_age: int = 60 * 60

    @model_validator(mode="after")
    def validate_allow_origins_and_credentials(self) -> Self:
        if self.allow_credentials is True and "*" in self.allow_origins:
            raise ValueError(
                "ALLOW_ORIGINS must not contain '*' when ALLOW_CREDENTIALS is True"
            )
        return self

    @model_validator(mode="after")
    def validate_app_secret(self) -> Self:
        if self.app_env != "local" and not self.app_secret.get_secret_value():
            raise ValueError("APP_SECRET must be set in non-local environments")
        return self

    @model_validator(mode="after")
    def validate_production_auth(self) -> Self:
        if self.auth_enabled is False and self.app_env == "production":
            raise ValueError("AUTH_ENABLED must be True in production")
        return self

    @model_validator(mode="after")
    def validate_debug_in_production(self) -> Self:
        if self.app_env == "production" and self.app_debug:
            raise ValueError("APP_DEBUG must be False in production")
        return self

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
                        f"{field_name} must not point to localhost in production"
                    )
        return self

    @model_validator(mode="after")
    def validate_email_tls_in_production(self) -> Self:
        if self.app_env == "production" and not self.email_tls:
            raise ValueError("EMAIL_TLS must be True in production")
        return self

    @model_validator(mode="after")
    def validate_production_credentials(self) -> Self:
        if self.app_env not in ("local", "development"):
            if not self.stripe_secret_key.get_secret_value():
                raise ValueError(
                    "STRIPE_SECRET_KEY must be set in non-local environments"
                )
            if not self.stripe_webhook_secret.get_secret_value():
                raise ValueError(
                    "STRIPE_WEBHOOK_SECRET must be set in non-local environments"
                )
        return self


settings = Settings()
