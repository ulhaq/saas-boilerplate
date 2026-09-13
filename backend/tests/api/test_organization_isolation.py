from fastapi.testclient import TestClient

# --- Organization isolation ---


def test_cannot_get_other_organization(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.get("/v1/organizations/1")
    assert response.status_code == 403


def test_cannot_patch_other_organization(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.patch(
        "/v1/organizations/1", json={"name": "Hacked"}
    )
    assert response.status_code == 403


def test_cannot_delete_other_organization(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.delete("/v1/organizations/1")
    assert response.status_code == 403


# --- User isolation ---


def test_cannot_delete_other_organization_user(
    organization2_admin_authenticated: TestClient,
) -> None:
    # org2 admin's active org is 2; user 1 is not in org 2, so 404
    response = organization2_admin_authenticated.delete("/v1/users/1")
    assert response.status_code == 404


def test_cannot_manage_roles_of_other_organization_user(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.post(
        "/v1/users/1/roles", json={"role_ids": [3]}
    )
    assert response.status_code == 404


# --- Role isolation ---


def test_cannot_get_other_organization_role(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.get("/v1/roles/1")
    assert response.status_code == 404


def test_cannot_patch_other_organization_role(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.patch(
        "/v1/roles/1", json={"name": "hacked"}
    )
    assert response.status_code == 404


def test_cannot_delete_other_organization_role(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.delete("/v1/roles/1")
    assert response.status_code == 404


def test_roles_list_only_shows_own_organization_roles(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.get("/v1/roles?page_size=50")
    assert response.status_code == 200
    rs = response.json()
    for role in rs["items"]:
        assert role["organization_id"] == 2


def test_new_role_not_visible_to_other_organization(
    admin_authenticated: TestClient, organization2_admin_authenticated: TestClient
) -> None:
    response = admin_authenticated.post(
        "/v1/roles", json={"name": "secret_role", "description": "Organization 1 only"}
    )
    assert response.status_code == 201

    response = organization2_admin_authenticated.get("/v1/roles?page_size=50")
    assert response.status_code == 200
    rs = response.json()
    role_names = [r["name"] for r in rs["items"]]
    assert "secret_role" not in role_names


# --- Cross-organization role assignment ---


def test_cannot_assign_other_organization_role_to_own_user(
    admin_authenticated: TestClient,
) -> None:
    # Role 5 belongs to Organization 2; user 2 belongs to Organization 1
    response = admin_authenticated.post("/v1/users/2/roles", json={"role_ids": [5]})
    assert response.status_code == 403
