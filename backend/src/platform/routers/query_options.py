from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, Query, Request

from src.platform.core.exceptions import ValidationException
from src.platform.enums import ComparisonOperator, ErrorCode
from src.platform.schemas.common import FilterItem

COMMON_SORTING_FIELDS = ["id", "name", "created_at", "updated_at"]
COMMON_FILTERING_FIELDS = ["id", "name", "created_at", "updated_at"]

_VALID_OPERATORS = {op.value for op in ComparisonOperator}


def sort_query(extra_fields: list[str] | None = None) -> Callable[..., list[str]]:
    valid_fields = COMMON_SORTING_FIELDS + (extra_fields or [])

    def dependency(
        sort: str = Query(
            default="id",
            description="Comma-separated list of fields to sort by.\n\n"
            "Use a leading `-` before a field name to indicate descending sort order.",
        ),
    ) -> list[str]:
        if not sort:
            return []

        sort_fields = [field.strip() for field in sort.split(",")]
        invalid_fields = [
            field_name
            for field in sort_fields
            if (field_name := field.lstrip("-")) not in valid_fields
        ]

        if invalid_fields:
            raise ValidationException(
                f"Invalid sort value(s): {', '.join(invalid_fields)}. "
                f"Allowed: {', '.join(valid_fields)}",
                error_code=ErrorCode.PARAMETER_INVALID,
            )

        return sort_fields

    return dependency


def filters_query(
    extra_fields: list[str] | None = None,
) -> Callable[..., list[FilterItem]]:
    valid_fields = set(COMMON_FILTERING_FIELDS + (extra_fields or []))

    def dependency(request: Request) -> list[FilterItem]:
        result: list[FilterItem] = []

        for key, raw_value in request.query_params.items():
            if "__" not in key:
                continue
            field, op_str = key.rsplit("__", 1)
            if field not in valid_fields:
                continue
            if op_str not in _VALID_OPERATORS:
                raise ValidationException(
                    f"Invalid operator '{op_str}' for field '{field}'. "
                    f"Allowed: {', '.join(sorted(_VALID_OPERATORS))}",
                    error_code=ErrorCode.PARAMETER_INVALID,
                )
            values = [v.strip() for v in raw_value.split(",")]
            result.append(
                FilterItem(field=field, op=ComparisonOperator(op_str), values=values)
            )

        return result

    return dependency


def search_query() -> Callable[..., str | None]:
    def dependency(
        q: str | None = Query(
            default=None,
            description="Search term. Case-insensitive match across searchable fields.",
        ),
    ) -> str | None:
        return q or None

    return dependency


SortQuery = Annotated[list[str], Depends(sort_query())]
FiltersQuery = Annotated[list[FilterItem], Depends(filters_query())]
SearchQuery = Annotated[str | None, Depends(search_query())]
PageSizeQuery = Annotated[int, Query(ge=5, le=100)]
PageNumberQuery = Annotated[int, Query(ge=1)]
