from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    organization_id: int
    type: str
    payload: dict[str, Any]
    read_at: datetime | None
    created_at: datetime


class UnreadCountOut(BaseModel):
    count: int
