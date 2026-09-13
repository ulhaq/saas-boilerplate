from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, Field

from src.platform.enums import ErrorCodeEnum
from src.platform.repositories.utils import ComparisonOperator


class ErrorResponse(BaseModel):
    time: Annotated[datetime, Field()]
    path: Annotated[str, Field()]
    method: Annotated[str, Field()]
    error_code: Annotated[str, Field()]
    msg: Annotated[str, Field()]

    def __init__(
        self, request: Request, error_code: ErrorCodeEnum, msg: str, **kwargs: Any
    ) -> None:
        super().__init__(
            time=datetime.now(UTC),
            path=str(request.url),
            method=request.method,
            error_code=error_code.code,
            msg=msg,
            **kwargs,
        )


class ValidationDetail(BaseModel):
    error_code: Annotated[str, Field()]
    field: Annotated[list[str | int], Field()]
    msg: Annotated[str, Field()]
    ctx: Annotated[Any, Field()]


class ValidationErrorResponse(ErrorResponse):
    errors: Annotated[list[ValidationDetail], Field()]

    def __init__(
        self, request: Request, error_code: ErrorCodeEnum, msg: str, **kwargs: Any
    ) -> None:
        kwargs["errors"] = [
            ValidationDetail(
                error_code=error["type"],
                field=error["loc"],
                msg=error["msg"],
                ctx=jsonable_encoder(error["ctx"]) if "ctx" in error else {},
            )
            for error in kwargs.get("errors", {})
        ]

        super().__init__(request=request, error_code=error_code, msg=msg, **kwargs)


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
