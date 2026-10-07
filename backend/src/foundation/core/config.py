from typing import Literal, Self

from pydantic import Field, SecretStr, computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import URL


def _parse_comma_list(value: str) -> list[str]:
    return [v.strip().rstrip("/") for v in value.split(",")]


class EnvSettings(BaseSettings):
    """Shared base for all settings classes: defines where settings are read
    from, nothing else. Product packages extend this with their own namespaced
    settings class (e.g. `ExampleSettings` with `env_prefix="example_"`)."""

    model_config = SettingsConfigDict(
        env_file="./.env",
        env_file_encoding="utf-8",
        extra="ignore",
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
    # Parts docker compose builds DB_CONNECTION from (see docker-compose*.yml)
    db_name: str = ""
    db_user: str = ""
    db_password: SecretStr = SecretStr("")
    postgres_port: int = 5432

    allow_multiple_organizations: bool = True

    auth_access_token_expiry: int = 15 * 60
    auth_refresh_token_expiry: int = 15 * 24 * 60 * 60
    auth_password_reset_expiry: int = 10 * 60
    email_verification_expiry: int = 60 * 60 * 24
    email_change_expiry: int = 60 * 60 * 24
    complete_registration_expiry: int = 30 * 60
    invite_expiry: int = 7 * 24 * 60 * 60

    mfa_enabled: bool = False
    mfa_challenge_expiry: int = 5 * 60
    mfa_recovery_code_count: int = 10
    mfa_max_failed_attempts: int = 5
    mfa_lockout_seconds: int = 15 * 60
    login_max_failed_attempts: int = 5
    login_lockout_seconds: int = 15 * 60

    raw_allow_origins: str = Field(
        default="http://localhost:5173",
        validation_alias="allow_origins",
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
    email_timeout_seconds: float = 10
    email_outbox_interval_seconds: int = 10
    email_from_address: str = "noreply@example.org"
    email_from_name: str = "SaaS Boilerplate"

    frontend_url: str = "http://localhost:5173"

    redis_url: str = "redis://localhost:6379/0"
    realtime_heartbeat_seconds: int = 25
    realtime_stream_max_seconds: int = 15 * 60

    rate_limit_enabled: bool = True

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

    # OpenTelemetry traces + metrics go to this OTLP/HTTP endpoint (e.g. the
    # Alloy agent at http://alloy:4318). Empty disables telemetry.
    otel_exporter_otlp_endpoint: str = ""

    permissions_cache_max_age: int = 60 * 60

    plans_cache_max_age: int = 60 * 60

    @model_validator(mode="after")
    def default_db_connection(self) -> Self:
        # Compose and CI always set DB_CONNECTION. Without it we're running on
        # the host machine (tests, alembic, init_db, dev server), so reach the
        # dev stack's postgres through the port it publishes on localhost.
        if self.db_connection:
            return self
        if self.app_env != "local":
            raise ValueError("DB_CONNECTION must be set in non-local environments")
        self.db_connection = URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password.get_secret_value(),
            host="localhost",
            port=self.postgres_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)
        return self

    @model_validator(mode="after")
    def validate_allow_origins_and_credentials(self) -> Self:
        if self.allow_credentials is True and "*" in self.allow_origins:
            raise ValueError(
                "ALLOW_ORIGINS must not contain '*' when ALLOW_CREDENTIALS is True",
            )
        return self

    @model_validator(mode="after")
    def validate_redis_url(self) -> Self:
        # Without Redis, events published by the worker or another API
        # replica never reach the app, and each replica keeps its own
        # rate-limit counters.
        if self.app_env != "local" and not self.redis_url:
            raise ValueError("REDIS_URL must be set in non-local environments")
        return self

    @model_validator(mode="after")
    def validate_app_secret(self) -> Self:
        if self.app_env != "local" and not self.app_secret.get_secret_value():
            raise ValueError("APP_SECRET must be set in non-local environments")
        return self

    @model_validator(mode="after")
    def validate_debug_in_production(self) -> Self:
        if self.app_env == "production" and self.app_debug:
            raise ValueError("APP_DEBUG must be False in production")
        return self

    @model_validator(mode="after")
    def validate_email_tls_in_production(self) -> Self:
        if self.app_env == "production" and not self.email_tls:
            raise ValueError("EMAIL_TLS must be True in production")
        return self


settings = Settings()
