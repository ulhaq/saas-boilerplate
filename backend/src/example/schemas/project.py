from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from src.platform.schemas.common import Timestamp


class ProjectBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: Annotated[str, Field(min_length=1, max_length=255)]
    description: str | None = None


class ProjectOut(ProjectBase, Timestamp):
    id: int
    organization_id: int


class ProjectIn(ProjectBase): ...


class ProjectPatch(BaseModel):
    name: Annotated[str | None, Field(min_length=1, max_length=255)] = None
    description: str | None = None
