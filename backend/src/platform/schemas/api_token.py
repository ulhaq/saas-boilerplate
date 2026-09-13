from datetime import UTC, datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, computed_field, field_validator

from src.platform.schemas.types import NonEmptyStr


class ApiTokenCreate(BaseModel):
    name: Annotated[NonEmptyStr, Field(max_length=100)]
    permissions: Annotated[list[str], Field(min_length=1)]
    expires_at: datetime | None = None

    @field_validator("expires_at")
    @classmethod
    def must_be_future(cls, v: datetime | None) -> datetime | None:
        if v is not None:
            expires = v if v.tzinfo is not None else v.replace(tzinfo=UTC)
            if expires <= datetime.now(UTC):
                raise ValueError("expires_at must be a future date")
        return v


class ApiTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    token_prefix: str
    permissions: list[str]
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    revoked_at: datetime | None

    @computed_field
    @property
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=UTC)
        return expires < datetime.now(UTC)


class ApiTokenCreatedResponse(ApiTokenResponse):
    token: str
