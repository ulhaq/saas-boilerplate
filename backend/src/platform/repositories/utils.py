from collections.abc import Callable
from datetime import datetime
from enum import Enum
from typing import Any

from dateutil import parser
from sqlalchemy import String, cast
from sqlalchemy.orm.attributes import InstrumentedAttribute

from src.platform.enums import ComparisonOperator


class FilterValueType(Enum):
    SINGLE = "single"
    LIST = "list"
    RANGE = "range"


# Mapping of field type to supported filter operators
FILTER_OPERATORS_BY_FIELD_TYPE = {
    str: [
        ComparisonOperator.EQUALS,
        ComparisonOperator.NOT_EQUALS,
        ComparisonOperator.CONTAINS,
        ComparisonOperator.INSENSITIVE_CONTAINS,
        ComparisonOperator.NOT_CONTAINS,
        ComparisonOperator.INSENSITIVE_NOT_CONTAINS,
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
    ],
    int: [
        ComparisonOperator.EQUALS,
        ComparisonOperator.NOT_EQUALS,
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL_TO,
        ComparisonOperator.GREATER_THAN,
        ComparisonOperator.GREATER_THAN_OR_EQUAL_TO,
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
        ComparisonOperator.BETWEEN,
    ],
    float: [
        ComparisonOperator.EQUALS,
        ComparisonOperator.NOT_EQUALS,
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL_TO,
        ComparisonOperator.GREATER_THAN,
        ComparisonOperator.GREATER_THAN_OR_EQUAL_TO,
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
        ComparisonOperator.BETWEEN,
    ],
    datetime: [
        ComparisonOperator.EQUALS,
        ComparisonOperator.NOT_EQUALS,
        ComparisonOperator.CONTAINS,
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL_TO,
        ComparisonOperator.GREATER_THAN,
        ComparisonOperator.GREATER_THAN_OR_EQUAL_TO,
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
        ComparisonOperator.BETWEEN,
    ],
    bool: [ComparisonOperator.EQUALS],
}


# Mapping of filter value types to allowed operators
COMPARISON_OPERATORS_BY_FILTER_VALUE_TYPE = {
    FilterValueType.SINGLE: [
        ComparisonOperator.EQUALS,
        ComparisonOperator.NOT_EQUALS,
        ComparisonOperator.LESS_THAN,
        ComparisonOperator.LESS_THAN_OR_EQUAL_TO,
        ComparisonOperator.GREATER_THAN,
        ComparisonOperator.GREATER_THAN_OR_EQUAL_TO,
        ComparisonOperator.CONTAINS,
        ComparisonOperator.INSENSITIVE_CONTAINS,
        ComparisonOperator.NOT_CONTAINS,
        ComparisonOperator.INSENSITIVE_NOT_CONTAINS,
    ],
    FilterValueType.LIST: [
        ComparisonOperator.IN,
        ComparisonOperator.NOT_IN,
    ],
    FilterValueType.RANGE: [
        ComparisonOperator.BETWEEN,
    ],
}

# SQLAlchemy operator lambda mapping
SQLA_OPERATORS: dict[ComparisonOperator, Callable[..., Any]] = {
    ComparisonOperator.EQUALS: lambda field, val: field == val,
    ComparisonOperator.NOT_EQUALS: lambda field, val: field != val,
    ComparisonOperator.LESS_THAN: lambda field, val: field < val,
    ComparisonOperator.LESS_THAN_OR_EQUAL_TO: lambda field, val: field <= val,
    ComparisonOperator.GREATER_THAN: lambda field, val: field > val,
    ComparisonOperator.GREATER_THAN_OR_EQUAL_TO: lambda field, val: field >= val,
    ComparisonOperator.CONTAINS: lambda field, val: cast(field, String).like(
        f"%{val}%"
    ),
    ComparisonOperator.INSENSITIVE_CONTAINS: lambda field, val: cast(
        field, String
    ).ilike(f"%{val}%"),
    ComparisonOperator.NOT_CONTAINS: lambda field, val: (
        ~cast(field, String).like(f"%{val}%")
    ),
    ComparisonOperator.INSENSITIVE_NOT_CONTAINS: lambda field, val: (
        ~cast(field, String).ilike(f"%{val}%")
    ),
    ComparisonOperator.IN: lambda field, val: field.in_(val),
    ComparisonOperator.NOT_IN: lambda field, val: ~field.in_(val),
    ComparisonOperator.BETWEEN: lambda field, start, end: field.between(start, end),
}


def get_filter_expression(
    operator: ComparisonOperator, values: list, field: InstrumentedAttribute
) -> list[Any] | Any:
    if operator in COMPARISON_OPERATORS_BY_FILTER_VALUE_TYPE[FilterValueType.SINGLE]:
        return [SQLA_OPERATORS[operator](field, value) for value in values]

    if operator in COMPARISON_OPERATORS_BY_FILTER_VALUE_TYPE[FilterValueType.LIST]:
        return SQLA_OPERATORS[operator](field, values)

    if operator in COMPARISON_OPERATORS_BY_FILTER_VALUE_TYPE[FilterValueType.RANGE]:
        if len(values) != 2:
            raise ValueError(
                "Between operator expects exactly two values: [start, end]"
            )
        return SQLA_OPERATORS[operator](field, values[0], values[1])

    return None


def cast_values_to_type(
    values: list, field_type: type, field_name: str, operator: ComparisonOperator
) -> list:
    try:
        if (
            operator == ComparisonOperator.CONTAINS
            and operator in FILTER_OPERATORS_BY_FIELD_TYPE[field_type]  # ty: ignore[invalid-argument-type]
        ):
            field_type = str

        rs = []
        for value in values:
            if field_type != datetime:
                rs.append(field_type(value))
            else:
                rs.append(parser.parse(value))
        return rs
    except (ValueError, TypeError) as exc:
        raise ValueError(
            f"Values for the '{field_name}' field must be provided "
            f"as a list of '{field_type.__name__}' types"
        ) from exc
