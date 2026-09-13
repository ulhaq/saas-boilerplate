"""Example product settings.

Independent settings namespace for the product: every field is read from the
environment with an `EXAMPLE_` prefix (e.g. `heartbeat_interval_seconds` <-
`EXAMPLE_HEARTBEAT_INTERVAL_SECONDS`).
"""

from pydantic_settings import SettingsConfigDict

from src.platform.core.config import EnvSettings


class ExampleSettings(EnvSettings):
    model_config = SettingsConfigDict(env_prefix="example_")

    heartbeat_interval_seconds: int = 60 * 60


settings = ExampleSettings()
