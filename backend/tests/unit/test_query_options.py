"""Tests for routers/query_options.py dependency factories."""

from unittest.mock import MagicMock

import pytest

from src.platform.core.exceptions import ValidationException
from src.platform.routers.query_options import filters_query, sort_query

# ---------------------------------------------------------------------------
# sort_query dependency
# ---------------------------------------------------------------------------


def test_sort_query_returns_empty_list_when_sort_is_empty():
    """sort_query dependency returns [] when sort is an empty string (line 27)."""
    dep = sort_query()
    result = dep(sort="")
    assert result == []


def test_sort_query_valid_field_returns_list():
    dep = sort_query()
    result = dep(sort="name,-created_at")
    assert result == ["name", "-created_at"]


def test_sort_query_invalid_field_raises():
    dep = sort_query()
    with pytest.raises(ValidationException):
        dep(sort="nonexistent_field")


def test_sort_query_extra_fields_accepted():
    dep = sort_query(extra_fields=["email", "status"])
    result = dep(sort="email,-status")
    assert result == ["email", "-status"]


# ---------------------------------------------------------------------------
# filters_query dependency
# ---------------------------------------------------------------------------


def _mock_request(params: dict) -> MagicMock:
    """Build a minimal mock Request with the given query_params dict."""
    req = MagicMock()
    req.query_params = params
    return req


def test_filters_query_skips_unknown_field():
    """
    filters_query silently skips a param whose field is not in valid_fields (line 61)
    """
    dep = filters_query()
    req = _mock_request({"unknown_field__eq": "val"})
    result = dep(req)
    assert result == []


def test_filters_query_skips_param_without_dunder():
    """Params without __ separator are ignored."""
    dep = filters_query()
    req = _mock_request({"page": "1", "sort": "name"})
    result = dep(req)
    assert result == []


def test_filters_query_valid_param_returns_filter_item():
    from src.platform.enums import ComparisonOperator
    from src.platform.schemas.common import FilterItem

    dep = filters_query()
    req = _mock_request({"name__eq": "Admin"})
    result = dep(req)
    assert len(result) == 1
    assert result[0] == FilterItem(
        field="name", op=ComparisonOperator.EQUALS, values=["Admin"]
    )


def test_filters_query_invalid_operator_raises():
    dep = filters_query()
    req = _mock_request({"name__bogus": "val"})
    with pytest.raises(ValidationException):
        dep(req)
