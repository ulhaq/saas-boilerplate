"""Tests for multi-organization user membership features:
- POST /auth/switch-organization
- GET  /organizations
- DELETE /users/{user_id}
- GET  /organizations/{organization_id}/users
- Login auto-selects most-recently-active organization
"""

from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _login(client: TestClient, email: str, password: str = "password") -> str:
    rs = client.post(
        "/v1/auth/token",
        data={"username": email, "password": password},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert rs.status_code == 200, rs.json()
    return rs.json()["access_token"]


def _auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# GET /organizations
# ---------------------------------------------------------------------------


def test_get_my_organizations_returns_own_organization(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.get("/v1/organizations")
    assert response.status_code == 200
    organizations = response.json()
    assert len(organizations) == 1
    assert organizations[0]["id"] == 1
    assert organizations[0]["name"] == "Acme Corp"


def test_get_my_organizations_after_joining_second_organization(
    admin_authenticated: TestClient,
    admin_in_org2: None,
) -> None:
    response = admin_authenticated.get("/v1/organizations")
    assert response.status_code == 200
    organizations = response.json()
    assert len(organizations) == 2
    organization_ids = {o["id"] for o in organizations}
    assert {1, 2} == organization_ids


def test_get_my_organizations_unauthenticated(client: TestClient) -> None:
    response = client.get("/v1/organizations")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# DELETE /users/{user_id}
# ---------------------------------------------------------------------------


def test_remove_user_from_organization(
    admin_authenticated: TestClient,
) -> None:
    # admin removes user 3 (no_roles) from Organization 1
    response = admin_authenticated.delete("/v1/users/3")
    assert response.status_code == 204

    # user 3 should no longer appear in Organization 1 users
    response = admin_authenticated.get("/v1/organizations/1/users")
    assert response.status_code == 200
    user_ids = [u["id"] for u in response.json()["items"]]
    assert 3 not in user_ids


def test_cannot_remove_nonmember_from_organization(
    organization2_admin_authenticated: TestClient,
) -> None:
    # user 2 (standard) is not in Organization 2; org-scoped lookup returns 404
    response = organization2_admin_authenticated.delete("/v1/users/2")
    assert response.status_code == 404


def test_cannot_remove_owner_from_organization(
    admin_authenticated: TestClient,
) -> None:
    # user 1 is the Owner - owner removal is blocked before the last-admin check
    response = admin_authenticated.delete("/v1/users/1")
    assert response.status_code == 403
    rs = response.json()
    assert rs["error_code"] == "owner_removal"


def test_cannot_remove_user_without_permission(
    standard_authenticated: TestClient,
) -> None:
    response = standard_authenticated.delete("/v1/users/3")
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# GET /organizations/{organization_id}/users
# ---------------------------------------------------------------------------


def test_get_organization_users(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/organizations/1/users")
    assert response.status_code == 200
    rs = response.json()
    assert rs["total"] == 3  # admin, standard, no_roles
    emails = {u["email"] for u in rs["items"]}
    assert "admin@example.org" in emails
    assert "standard@example.org" in emails
    assert "no_roles@example.org" in emails


def test_get_organization_users_shows_only_organization_roles(
    admin_authenticated: TestClient,
    admin_in_org2: None,
) -> None:
    # Organization 1 user list: admin's roles should be Organization 1 roles only.
    response = admin_authenticated.get("/v1/organizations/1/users")
    assert response.status_code == 200
    admin_user = next(
        u for u in response.json()["items"] if u["email"] == "admin@example.org"
    )
    for role in admin_user["roles"]:
        assert role["organization_id"] == 1


def test_cannot_get_users_of_other_organization(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.get("/v1/organizations/2/users")
    assert response.status_code == 403


def test_cannot_get_organization_users_without_read_user_permission(
    client: TestClient,
) -> None:
    # no_roles user has no permissions at all
    token = _login(client, "no_roles@example.org")
    response = client.get("/v1/organizations/1/users", headers=_auth_headers(token))
    assert response.status_code == 403


# ---------------------------------------------------------------------------
# POST /auth/switch-organization
# ---------------------------------------------------------------------------


def test_switch_organization(
    client: TestClient,
    admin_in_org2: None,
) -> None:
    # Login as admin (currently active in Organization 1)
    token = _login(client, "admin@example.org")

    # Switch to Organization 2
    response = client.post(
        "/v1/auth/switch-organization",
        json={"organization_id": 2},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    new_token = response.json()["access_token"]
    assert new_token
    assert new_token != token


def test_switch_organization_context_changes(
    client: TestClient,
    admin_in_org2: None,
) -> None:
    token = _login(client, "admin@example.org")

    # Active in Organization 1 - /users/me shows Admin role
    me_o1 = client.get("/v1/users/me", headers=_auth_headers(token)).json()
    assert len(me_o1["roles"]) == 1
    assert me_o1["roles"][0]["name"] == "Owner"

    # Switch to Organization 2
    switch_rs = client.post(
        "/v1/auth/switch-organization",
        json={"organization_id": 2},
        headers=_auth_headers(token),
    )
    new_token = switch_rs.json()["access_token"]

    # Active in Organization 2 - no roles there, so /users/me shows empty roles
    me_o2 = client.get("/v1/users/me", headers=_auth_headers(new_token)).json()
    assert me_o2["roles"] == []


def test_cannot_switch_to_organization_not_a_member_of(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.post(
        "/v1/auth/switch-organization", json={"organization_id": 2}
    )
    assert response.status_code == 403


def test_switch_organization_requires_auth(client: TestClient) -> None:
    response = client.post("/v1/auth/switch-organization", json={"organization_id": 1})
    assert response.status_code == 401


def test_switch_organization_sets_refresh_token_cookie(
    client: TestClient,
    admin_in_org2: None,
) -> None:
    token = _login(client, "admin@example.org")

    response = client.post(
        "/v1/auth/switch-organization",
        json={"organization_id": 2},
        headers=_auth_headers(token),
    )
    assert response.status_code == 200
    assert "refresh_token=" in response.headers.get("set-cookie", "")


def test_switch_organization_rotates_refresh_token(
    client: TestClient,
    admin_in_org2: None,
) -> None:
    # Login to get initial tokens
    login_rs = client.post(
        "/v1/auth/token",
        data={"username": "admin@example.org", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    old_refresh = login_rs.json()["refresh_token"]
    access_token = login_rs.json()["access_token"]

    # Switch organization
    client.post(
        "/v1/auth/switch-organization",
        json={"organization_id": 2},
        headers=_auth_headers(access_token),
    )

    # Old refresh token must no longer work
    client.cookies.set("refresh_token", old_refresh)
    response = client.post("/v1/auth/refresh")
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# Login auto-selects most-recently-active organization
# ---------------------------------------------------------------------------


def test_login_auto_selects_most_recently_active_organization(
    client: TestClient,
    admin_in_org2: None,
) -> None:
    # Login and switch to Organization 2 (updates last_active_at for Organization 2)
    first_token = _login(client, "admin@example.org")
    switch_rs = client.post(
        "/v1/auth/switch-organization",
        json={"organization_id": 2},
        headers=_auth_headers(first_token),
    )
    assert switch_rs.status_code == 200

    # Re-login: should auto-select Organization 2 (most recently active)
    # Organization 2 has no roles for admin, so /users/me should return empty roles
    new_token = _login(client, "admin@example.org")
    me = client.get("/v1/users/me", headers=_auth_headers(new_token)).json()
    assert me["roles"] == []


def test_login_selects_first_organization_when_none_active(
    client: TestClient,
) -> None:
    # admin@example.org belongs to Organization 1; last_active_at is set from seeding.
    token = _login(client, "admin@example.org")
    response = client.get("/v1/organizations", headers=_auth_headers(token))
    assert response.status_code == 200
    rs = response.json()
    assert len(rs) == 1
    assert rs[0]["name"] == "Acme Corp"


# ---------------------------------------------------------------------------
# Roles are isolated per organization
# ---------------------------------------------------------------------------


def test_roles_shown_are_scoped_to_active_organization(
    client: TestClient,
    admin_in_org2: None,
) -> None:
    # While active in Organization 1, /users/me shows Organization 1 roles
    token_o1 = _login(client, "admin@example.org")
    me_o1 = client.get("/v1/users/me", headers=_auth_headers(token_o1)).json()
    assert all(r["organization_id"] == 1 for r in me_o1["roles"])

    # After switching to Organization 2, /users/me shows no roles (none assigned there)
    switch_rs = client.post(
        "/v1/auth/switch-organization",
        json={"organization_id": 2},
        headers=_auth_headers(token_o1),
    )
    token_o2 = switch_rs.json()["access_token"]
    me_o2 = client.get("/v1/users/me", headers=_auth_headers(token_o2)).json()
    assert me_o2["roles"] == []


# ---------------------------------------------------------------------------
# Cross-organization mutation isolation
# ---------------------------------------------------------------------------


def test_cannot_update_organization_you_are_not_active_in(
    admin_authenticated: TestClient,
    admin_in_org2: None,
) -> None:
    # admin is active in Organization 1 - cannot update Organization 2
    response = admin_authenticated.patch(
        "/v1/organizations/2", json={"name": "Hijacked"}
    )
    assert response.status_code == 403


def test_cannot_delete_organization_you_are_not_active_in(
    admin_authenticated: TestClient,
    admin_in_org2: None,
) -> None:
    # admin is active in Organization 1 - cannot delete Organization 2
    response = admin_authenticated.delete("/v1/organizations/2")
    assert response.status_code == 403


def test_cannot_transfer_ownership_of_organization_you_are_not_active_in(
    client: TestClient,
    admin_in_org2: None,
) -> None:
    # Login as admin (active in Organization 1) and try to transfer ownership of Org 2
    token = _login(client, "admin@example.org")
    response = client.post(
        "/v1/organizations/2/transfer-ownership",
        json={"user_id": 4},
        headers=_auth_headers(token),
    )
    assert response.status_code == 403
