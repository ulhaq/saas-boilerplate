from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, computed_field


class InvitationInviterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str


class InvitationRoleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str


class InvitationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    role_ids: list[int]
    roles: list[InvitationRoleOut] = []
    invited_by: InvitationInviterOut | None
    created_at: datetime
    expires_at: datetime

    @computed_field
    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)
