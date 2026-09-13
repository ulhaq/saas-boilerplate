import pytest
from fastapi.testclient import TestClient

from tests.utils import (
    assert_filtering_of_items_list,
    assert_pagination,
    assert_sorting_of_items_list,
)


def test_get_all_permissions(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/permissions?page_size=100")
    assert response.status_code == 200
    assert "max-age" in response.headers["cache-control"]
    rs = response.json()

    assert rs["page_number"] == 1
    assert rs["page_size"] == 100
    assert rs["total"] == 17

    assert len(rs["items"]) == 17
    assert rs["items"][0]["id"] == 1
    assert rs["items"][0]["name"] == "update:organization"
    assert (
        rs["items"][0]["description"]
        == "Allows the user to update organization accounts."
    )
    assert rs["items"][0]["created_at"]
    assert rs["items"][0]["updated_at"]


@pytest.mark.parametrize(
    "page_number, page_size, page_total, total",
    [
        (1, 10, 10, 17),
        (2, 10, 7, 17),
        (3, 10, 0, 17),
    ],
)
def test_paginate_permissions(
    page_number: int,
    page_size: int,
    page_total: int,
    total: int,
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.get(
        f"/v1/permissions?page_number={page_number}&page_size{page_size}"
    )
    assert response.status_code == 200
    rs = response.json()

    assert_pagination(rs, page_number, page_size, page_total, total)


@pytest.mark.parametrize(
    "sort",
    [
        ("id"),
        ("-id"),
        ("name"),
        ("-name"),
        ("description"),
        ("-description"),
        ("name,description"),
        ("-name,-description"),
        ("-name,description"),
        ("name,-description"),
        ("created_at"),
        ("-created_at"),
        ("updated_at"),
        ("-updated_at"),
    ],
)
def test_sort_permissions(sort: str, admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get(f"/v1/permissions?sort={sort}")
    assert response.status_code == 200
    rs = response.json()

    assert_sorting_of_items_list(rs["items"], sort.split(","))


@pytest.mark.parametrize(
    "fields, values, operators, total",
    [
        # Single field, single value
        (["id"], [[1]], ["eq"], 1),
        (["name"], [["read:user"]], ["eq"], 1),
        (
            ["name"],
            [["read:"]],
            ["co"],
            5,
        ),  # read:user, read:role, read:permission,
        # read:audit_log, read:project
        (["id"], [[15]], ["gt"], 2),  # ids 16, 18
        (["id"], [[10]], ["gte"], 8),  # ids 10-18
        # Single field, multiple values
        (["id"], [[0, 1]], ["between"], 1),
        (["id"], [[1, 2]], ["between"], 2),
        (["id"], [[2, 3]], ["between"], 2),
        (["id"], [[1, 5, 10]], ["in"], 3),
        (["name"], [["read:user", "read:role"]], ["in"], 2),
        (["description"], [["allows"]], ["ico"], 17),
        (
            ["created_at"],
            [["2025-04-22T14:04:38.586226", "2050-09-22T14:04:38.586226"]],
            ["between"],
            17,
        ),
    ],
)
def test_filter_permissions(
    fields: list[str],
    values: list[list],
    operators: list[str],
    total: int,
    admin_authenticated: TestClient,
) -> None:
    params = "&".join(
        f"{field}__{op}={','.join(str(v) for v in value)}"
        for field, value, op in zip(fields, values, operators, strict=False)
    )
    response = admin_authenticated.get(f"/v1/permissions?{params}&page_size=50")
    assert response.status_code == 200
    rs = response.json()

    assert len(rs["items"]) == total

    filter_data = list(zip(fields, values, operators, strict=False))
    assert_filtering_of_items_list(rs["items"], filter_data)


@pytest.mark.parametrize(
    "params, total",
    [
        # AND: id <= 5 (5 permissions)
        # AND name contains "read" (read:user=4, read:role=5) > 2
        ("id__lte=5&name__ico=read", 2),
        # AND: name contains "manage" (5) AND id >= 9 (manage:user_role=9 onwards) > 4
        ("name__ico=manage&id__gte=9", 3),
        # AND: id between 1 and 4 AND name ico "read" > 1 (read:user=4)
        ("id__between=1,4&name__ico=read", 2),
    ],
)
def test_filter_permissions_multi_field(
    params: str,
    total: int,
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.get(f"/v1/permissions?{params}&page_size=50")
    assert response.status_code == 200
    assert response.json()["total"] == total


def test_retrieve_a_permission(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/permissions/1")
    assert response.status_code == 200
    rs = response.json()

    assert rs["id"] == 1
    assert rs["name"] == "update:organization"
    assert rs["description"] == "Allows the user to update organization accounts."
    assert rs["created_at"]
    assert rs["updated_at"]


def test_cannot_get_non_existent_permission(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/permissions/0")
    assert response.status_code == 404
    rs = response.json()
    assert rs["msg"] == "Permission not found. [identifier=0]"


def test_cannot_get_permissions_while_unauthorized(
    no_roles_authenticated: TestClient,
) -> None:
    response = no_roles_authenticated.get("/v1/permissions")
    assert response.status_code == 403
    rs = response.json()
    assert rs["msg"] == "You are not authorized to perform this action"


def test_cannot_retrieve_a_permission_while_unauthorized(
    no_roles_authenticated: TestClient,
) -> None:
    response = no_roles_authenticated.get("/v1/permissions/1")
    assert response.status_code == 403
    rs = response.json()
    assert rs["msg"] == "You are not authorized to perform this action"
