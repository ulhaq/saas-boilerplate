"""The JSON body of every API error response.

Lives in core next to the exceptions it serialises, so the error middleware and
the exception handlers in `main.py` can build it without importing `schemas`.
"""

from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, Field

from src.platform.enums import ErrorCodeEnum


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
    ctx: Annotated[dict[str, Any], Field()]


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
