from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.foundation.core.schema import ResponseSchema


class InvitationInviterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class InvitationRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class InvitationOut(ResponseSchema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role_ids: list[int]
    roles: list[InvitationRoleOut] = Field(default_factory=list)
    invited_by: InvitationInviterOut | None
    created_at: datetime
    expires_at: datetime

    @computed_field
    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)
