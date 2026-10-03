from pydantic import BaseModel, ConfigDict

from src.foundation.core.schema import ResponseSchema
from src.foundation.schemas.common import Timestamp


class PermissionBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str | None = None


class PermissionOut(PermissionBase, Timestamp, ResponseSchema):
    id: int


class PermissionIn(PermissionBase): ...


class PermissionPatch(BaseModel):
    name: str | None = None
    description: str | None = None
