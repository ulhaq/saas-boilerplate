from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.platform.enums import AuditAction


def test_get_audit_logs_forbidden_for_member(
    standard_authenticated: TestClient,
) -> None:
    response = standard_authenticated.get("/v1/audit-logs")
    assert response.status_code == 403


def test_get_audit_logs_forbidden_without_auth(client: TestClient) -> None:
    response = client.get("/v1/audit-logs")
    assert response.status_code == 401


def test_login_creates_auth_login_entry(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/audit-logs")
    assert response.status_code == 200
    rs = response.json()

    login_entries = [e for e in rs["items"] if e["action"] == AuditAction.AUTH_LOGIN]
    assert len(login_entries) >= 1

    entry = login_entries[0]
    assert entry["user_id"] is not None
    assert entry["organization_id"] is not None
    assert entry["created_at"] is not None


def test_ip_address_is_captured(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/audit-logs")
    assert response.status_code == 200
    rs = response.json()

    assert rs["total"] >= 1
    for entry in rs["items"]:
        assert entry["ip_address"] is not None


def test_invite_user_creates_audit_entry(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    mocker.patch("src.platform.services.user.send_email")

    admin_authenticated.post(
        "/v1/users/invite", json={"email": "invited@test.com", "role_ids": [3]}
    )

    response = admin_authenticated.get(
        "/v1/audit-logs", params={"action": AuditAction.USER_INVITE}
    )
    assert response.status_code == 200
    rs = response.json()

    assert rs["total"] == 1
    entry = rs["items"][0]
    assert entry["action"] == AuditAction.USER_INVITE
    assert entry["resource_type"] == "user"
    assert entry["details"]["email"] == "invited@test.com"


def test_role_create_creates_audit_entry(admin_authenticated: TestClient) -> None:
    admin_authenticated.post(
        "/v1/roles", json={"name": "TestRole", "description": "Test"}
    )

    response = admin_authenticated.get(
        "/v1/audit-logs", params={"action": AuditAction.ROLE_CREATE}
    )
    rs = response.json()

    assert rs["total"] == 1
    entry = rs["items"][0]
    assert entry["action"] == AuditAction.ROLE_CREATE
    assert entry["resource_type"] == "role"
    assert entry["details"]["name"] == "TestRole"


def test_role_delete_creates_audit_entry(admin_authenticated: TestClient) -> None:
    create_rs = admin_authenticated.post(
        "/v1/roles", json={"name": "ToDelete", "description": "x"}
    )
    role_id = create_rs.json()["id"]

    admin_authenticated.delete(f"/v1/roles/{role_id}")

    response = admin_authenticated.get(
        "/v1/audit-logs", params={"action": AuditAction.ROLE_DELETE}
    )
    rs = response.json()

    assert rs["total"] == 1
    entry = rs["items"][0]
    assert entry["action"] == AuditAction.ROLE_DELETE
    assert entry["resource_id"] == role_id


def test_api_token_create_creates_audit_entry(admin_authenticated: TestClient) -> None:
    create_rs = admin_authenticated.post(
        "/v1/api-tokens",
        json={"name": "mytoken", "permissions": ["manage:api_token"]},
    )
    token_id = create_rs.json()["id"]

    response = admin_authenticated.get(
        "/v1/audit-logs", params={"action": AuditAction.API_TOKEN_CREATE}
    )
    rs = response.json()

    assert rs["total"] == 1
    entry = rs["items"][0]
    assert entry["action"] == AuditAction.API_TOKEN_CREATE
    assert entry["resource_type"] == "api_token"
    assert entry["resource_id"] == token_id
    assert entry["details"]["name"] == "mytoken"


def test_api_token_revoke_creates_audit_entry(admin_authenticated: TestClient) -> None:
    create_rs = admin_authenticated.post(
        "/v1/api-tokens",
        json={"name": "todelete", "permissions": ["manage:api_token"]},
    )
    token_id = create_rs.json()["id"]

    admin_authenticated.delete(f"/v1/api-tokens/{token_id}")

    response = admin_authenticated.get(
        "/v1/audit-logs", params={"action": AuditAction.API_TOKEN_DELETE}
    )
    rs = response.json()

    assert rs["total"] == 1
    entry = rs["items"][0]
    assert entry["action"] == AuditAction.API_TOKEN_DELETE
    assert entry["resource_id"] == token_id


def test_audit_log_org_isolation(
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    # Org 1 admin creates a role - generates a ROLE_CREATE log entry for org 1
    admin_authenticated.post(
        "/v1/roles", json={"name": "OrgIsolatedRole", "description": "x"}
    )

    # Org 2 admin should see no ROLE_CREATE entries (none in their org)
    response = organization2_admin_authenticated.get(
        "/v1/audit-logs", params={"action": AuditAction.ROLE_CREATE}
    )
    rs = response.json()
    assert rs["total"] == 0


def test_audit_log_action_filter(admin_authenticated: TestClient) -> None:
    # Create a role to generate a ROLE_CREATE entry alongside the existing AUTH_LOGIN
    admin_authenticated.post("/v1/roles", json={"name": "Filtered", "description": "x"})

    # Unfiltered: multiple entries exist
    all_rs = admin_authenticated.get("/v1/audit-logs").json()
    assert all_rs["total"] >= 2

    # Filtered to role.create only: exactly 1
    filtered_rs = admin_authenticated.get(
        "/v1/audit-logs", params={"action": AuditAction.ROLE_CREATE}
    ).json()
    assert filtered_rs["total"] == 1
    assert all(e["action"] == AuditAction.ROLE_CREATE for e in filtered_rs["items"])


def test_audit_log_pagination(admin_authenticated: TestClient) -> None:
    # Create two roles to ensure multiple entries
    admin_authenticated.post("/v1/roles", json={"name": "Role1", "description": "x"})
    admin_authenticated.post("/v1/roles", json={"name": "Role2", "description": "x"})

    # Page 1 with size 10 (minimum)
    response = admin_authenticated.get(
        "/v1/audit-logs", params={"page_size": 10, "page_number": 1}
    )
    assert response.status_code == 200
    rs = response.json()
    assert rs["page_number"] == 1
    assert rs["page_size"] == 10
    assert rs["total"] >= 3  # 1 login + 2 role creates
    assert len(rs["items"]) <= 10

    # Items ordered newest first
    created_ats = [e["created_at"] for e in rs["items"]]
    assert created_ats == sorted(created_ats, reverse=True)


def test_audit_log_response_shape(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/audit-logs")
    assert response.status_code == 200
    rs = response.json()

    assert "items" in rs
    assert "total" in rs
    assert "page_number" in rs
    assert "page_size" in rs

    entry = rs["items"][0]
    assert "id" in entry
    assert "organization_id" in entry
    assert "user_id" in entry
    assert "action" in entry
    assert "resource_type" in entry
    assert "resource_id" in entry
    assert "ip_address" in entry
    assert "details" in entry
    assert "created_at" in entry
