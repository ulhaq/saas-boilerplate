"""Nobody can hand out more access than they hold: granting or revoking a
permission - through a role's permissions, a user's roles or an invitation -
needs the caller to hold it (`assert_can_grant`). Owners hold every one."""

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.main import app

# A manager who may manage roles and members, but not read the audit log.
MANAGER_PERMISSIONS = [
    "read:user",
    "read:role",
    "read:permission",
    "create:role",
    "manage:role_permission",
    "manage:user_role",
    "manage:organization_user",
]
MANAGER, OTHER_MEMBER = 2, 3  # seeded in organization 1


def _login(email: str) -> TestClient:
    client = TestClient(app)
    token = client.post(
        "/v1/auth/token",
        data={"username": email, "password": "password"},
    ).json()["access_token"]
    client.headers["Authorization"] = f"Bearer {token}"
    return client


def _role(owner: TestClient, name: str, permissions: list[str], ids: dict) -> int:
    role_id = owner.post("/v1/roles", json={"name": name}).json()["id"]
    response = owner.post(
        f"/v1/roles/{role_id}/permissions",
        json={"permission_ids": [ids[p] for p in permissions]},
    )
    assert response.status_code == 200, response.text
    return role_id


def _refused(response) -> None:
    assert response.status_code == 403, response.text
    assert response.json()["error_code"] == "permission_not_held"


@pytest.fixture
def setup() -> dict:
    owner = _login("admin@example.org")
    ids = {
        p["name"]: p["id"]
        for p in owner.get("/v1/permissions?page_size=100").json()["items"]
    }
    manager_role = _role(owner, "Manager", MANAGER_PERMISSIONS, ids)
    auditor_role = _role(owner, "Auditor", ["read:audit_log"], ids)
    owner.post(f"/v1/users/{MANAGER}/roles", json={"role_ids": [manager_role]})
    return {
        "owner": owner,
        "manager": _login("standard@example.org"),
        "ids": ids,
        "auditor_role": auditor_role,
    }


def test_a_role_can_only_get_permissions_its_editor_holds(setup):
    manager, ids = setup["manager"], setup["ids"]
    role_id = manager.post("/v1/roles", json={"name": "Mine"}).json()["id"]

    held = manager.post(
        f"/v1/roles/{role_id}/permissions",
        json={"permission_ids": [ids["read:user"]]},
    )
    assert held.status_code == 200
    _refused(
        manager.post(
            f"/v1/roles/{role_id}/permissions",
            json={"permission_ids": [ids["read:user"], ids["read:audit_log"]]},
        ),
    )

    # The owner may: they hold every permission.
    owner = setup["owner"]
    response = owner.post(
        f"/v1/roles/{role_id}/permissions",
        json={"permission_ids": [ids["read:user"], ids["read:audit_log"]]},
    )
    assert response.status_code == 200
    # ...and the manager can't take back what they don't hold either.
    _refused(
        manager.post(
            f"/v1/roles/{role_id}/permissions",
            json={"permission_ids": [ids["read:user"]]},
        ),
    )


def test_a_user_can_only_be_given_or_stripped_of_roles_the_caller_could_grant(
    setup,
):
    manager, owner, auditor = setup["manager"], setup["owner"], setup["auditor_role"]

    _refused(
        manager.post(f"/v1/users/{OTHER_MEMBER}/roles", json={"role_ids": [auditor]}),
    )
    owner.post(f"/v1/users/{OTHER_MEMBER}/roles", json={"role_ids": [auditor]})
    _refused(manager.post(f"/v1/users/{OTHER_MEMBER}/roles", json={"role_ids": []}))


def test_an_invite_can_only_carry_roles_the_inviter_could_grant(
    setup,
    mocker: MockerFixture,
):
    mocker.patch("src.foundation.services.user.send_email")
    manager, auditor = setup["manager"], setup["auditor_role"]

    _refused(
        manager.post(
            "/v1/users/invite",
            json={"email": "new@example.org", "role_ids": [auditor]},
        ),
    )
    # A role within the manager's own permissions is fine.
    reader = _role(setup["owner"], "Reader", ["read:user"], setup["ids"])
    response = manager.post(
        "/v1/users/invite",
        json={"email": "new@example.org", "role_ids": [reader]},
    )
    assert response.status_code == 204
