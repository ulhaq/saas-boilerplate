from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from src.platform.schemas.common import Timestamp
from src.platform.schemas.types import NonEmptyStr


class OrganizationBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Annotated[NonEmptyStr, Field(max_length=255)]


class OrganizationOut(OrganizationBase, Timestamp):
    id: int


class MyOrganizationOut(OrganizationOut):
    is_owner: bool = False


class OrganizationPatch(BaseModel):
    name: Annotated[NonEmptyStr, Field(max_length=255)] | None = None


class TransferOwnershipIn(BaseModel):
    user_id: int
