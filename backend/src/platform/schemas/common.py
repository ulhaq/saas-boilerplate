from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from src.platform.enums import ComparisonOperator


class Timestamp(BaseModel):
    created_at: datetime
    updated_at: datetime | None


class NameDescriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None = None


class PaginatedResponse[SchemaOutType: BaseModel](BaseModel):
    items: Sequence[SchemaOutType]
    page_number: int
    page_size: int
    total: int


@dataclass
class FilterItem:
    field: str
    op: ComparisonOperator
    values: list[str]


class PageQueryParams(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    sort: list[str]
    filters: list[FilterItem]
    page_size: int
    page_number: int
    search: str | None = None
