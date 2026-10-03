from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from src.foundation.core.schema import ResponseSchema


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    organization_id: int
    notification_type: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int


class NotificationPreferenceOut(ResponseSchema):
    category: str
    in_app: bool
    email: bool
    # The email can't be turned off (account-critical).
    email_required: bool


class NotificationPreferenceIn(BaseModel):
    category: str
    in_app: bool
    email: bool
