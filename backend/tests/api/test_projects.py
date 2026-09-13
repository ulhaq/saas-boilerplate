from fastapi.testclient import TestClient

from src.example.enums import ExampleUsageMetric
from src.platform.models.billing import PlanSetting
from tests.conftest import TestSessionLocal

_FREE_PLAN_ID = 1  # seeded in conftest


async def _set_project_limit(limit_value: int | None) -> None:
    async with TestSessionLocal() as session:
        session.add(
            PlanSetting(
                plan_id=_FREE_PLAN_ID,
                key=ExampleUsageMetric.PROJECTS,
                value=limit_value,
            )
        )
        await session.commit()


def _create(client: TestClient, name: str, description: str | None = None) -> dict:
    response = client.post(
        "/v1/projects", json={"name": name, "description": description}
    )
    assert response.status_code == 201, response.text
    return response.json()


def test_create_a_project(admin_authenticated: TestClient) -> None:
    rs = _create(admin_authenticated, "Website relaunch", "Q3 marketing site")

    assert rs["id"]
    assert rs["name"] == "Website relaunch"
    assert rs["description"] == "Q3 marketing site"
    assert rs["organization_id"] == 1
    assert rs["created_at"]
    assert rs["updated_at"]


def test_list_projects(admin_authenticated: TestClient) -> None:
    _create(admin_authenticated, "Alpha")
    _create(admin_authenticated, "Beta")

    response = admin_authenticated.get("/v1/projects?sort=name")
    assert response.status_code == 200
    rs = response.json()
    assert rs["total"] == 2
    assert [p["name"] for p in rs["items"]] == ["Alpha", "Beta"]


def test_search_projects(admin_authenticated: TestClient) -> None:
    _create(admin_authenticated, "Alpha", "internal tooling")
    _create(admin_authenticated, "Beta", "customer portal")

    response = admin_authenticated.get("/v1/projects?q=portal")
    assert response.status_code == 200
    assert [p["name"] for p in response.json()["items"]] == ["Beta"]


def test_retrieve_a_project(admin_authenticated: TestClient) -> None:
    created = _create(admin_authenticated, "Alpha")

    response = admin_authenticated.get(f"/v1/projects/{created['id']}")
    assert response.status_code == 200
    assert response.json()["name"] == "Alpha"


def test_patch_a_project(admin_authenticated: TestClient) -> None:
    created = _create(admin_authenticated, "Alpha", "old")

    response = admin_authenticated.patch(
        f"/v1/projects/{created['id']}", json={"description": "new"}
    )
    assert response.status_code == 200
    rs = response.json()
    assert rs["name"] == "Alpha"
    assert rs["description"] == "new"


def test_delete_a_project(admin_authenticated: TestClient) -> None:
    created = _create(admin_authenticated, "Alpha")

    response = admin_authenticated.delete(f"/v1/projects/{created['id']}")
    assert response.status_code == 204

    response = admin_authenticated.get(f"/v1/projects/{created['id']}")
    assert response.status_code == 404


def test_cannot_create_duplicate_project_name(admin_authenticated: TestClient) -> None:
    _create(admin_authenticated, "Alpha")

    response = admin_authenticated.post("/v1/projects", json={"name": "Alpha"})
    assert response.status_code == 409
    assert response.json()["error_code"] == "project_name_taken"


def test_cannot_rename_project_to_existing_name(
    admin_authenticated: TestClient,
) -> None:
    _create(admin_authenticated, "Alpha")
    beta = _create(admin_authenticated, "Beta")

    response = admin_authenticated.patch(
        f"/v1/projects/{beta['id']}", json={"name": "Alpha"}
    )
    assert response.status_code == 409


def test_cannot_create_project_with_empty_name(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.post("/v1/projects", json={"name": ""})
    assert response.status_code == 422


async def test_cannot_create_project_beyond_plan_limit(
    admin_authenticated: TestClient,
) -> None:
    await _set_project_limit(1)
    _create(admin_authenticated, "Alpha")

    response = admin_authenticated.post("/v1/projects", json={"name": "Beta"})
    assert response.status_code == 402
    assert response.json()["error_code"] == "capacity_exceeded"


async def test_unlimited_plan_allows_many_projects(
    admin_authenticated: TestClient,
) -> None:
    await _set_project_limit(None)
    for i in range(5):
        _create(admin_authenticated, f"Project {i}")


def test_projects_are_organization_isolated(
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    created = _create(admin_authenticated, "Org 1 project")

    rs = organization2_admin_authenticated.get("/v1/projects").json()
    assert rs["total"] == 0

    response = organization2_admin_authenticated.get(f"/v1/projects/{created['id']}")
    assert response.status_code == 404
    response = organization2_admin_authenticated.delete(f"/v1/projects/{created['id']}")
    assert response.status_code == 404


def test_same_project_name_allowed_in_different_organizations(
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    _create(admin_authenticated, "Shared name")
    _create(organization2_admin_authenticated, "Shared name")


def test_member_role_can_manage_projects(standard_authenticated: TestClient) -> None:
    created = _create(standard_authenticated, "Member project")
    response = standard_authenticated.delete(f"/v1/projects/{created['id']}")
    assert response.status_code == 204


def test_cannot_list_projects_without_permission(
    no_roles_authenticated: TestClient,
) -> None:
    response = no_roles_authenticated.get("/v1/projects")
    assert response.status_code == 403


def test_cannot_create_project_without_permission(
    no_roles_authenticated: TestClient,
) -> None:
    response = no_roles_authenticated.post("/v1/projects", json={"name": "Nope"})
    assert response.status_code == 403


def test_projects_require_authentication(client: TestClient) -> None:
    assert client.get("/v1/projects").status_code == 401
