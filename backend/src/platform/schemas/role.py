from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from src.platform.schemas.common import NameDescriptionOut, Timestamp
from src.platform.schemas.utils import sort_by_id


class RoleBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    description: str | None = None


class RoleOut(RoleBase, Timestamp):
    id: int
    organization_id: int
    is_protected: bool = False
    permissions: Annotated[list[NameDescriptionOut], AfterValidator(sort_by_id)] = (
        Field(default_factory=list)
    )


class RoleIn(RoleBase): ...


class RolePatch(BaseModel):
    name: str | None = None
    description: str | None = None


class RolePermissionIn(BaseModel):
    permission_ids: list[int] = Field(default_factory=list)
