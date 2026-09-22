from unittest.mock import patch

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

from src.main import app


def _invite(
    mocker: MockerFixture,
    client: TestClient,
    email: str = "invited@example.org",
    role_ids: list[int] | None = None,
) -> str:
    """Send an invite and return the link token captured from the email."""
    mock_send = mocker.patch("src.platform.services.user.send_email")
    rs = client.post(
        "/v1/users/invite",
        json={"email": email, "role_ids": role_ids if role_ids is not None else [2]},
    )
    assert rs.status_code == 204, rs.text
    return mock_send.call_args.kwargs["data"]["invite_url"].split("token=")[1]


# --- GET /invitations -------------------------------------------------------


def test_list_invitations(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    _invite(mocker, admin_authenticated)

    rs = admin_authenticated.get("/v1/invitations")
    assert rs.status_code == 200
    [item] = rs.json()
    assert item["email"] == "invited@example.org"
    assert item["role_ids"] == [2]
    assert item["roles"] == [{"id": 2, "name": "Member"}]
    assert item["invited_by"]["email"] == "admin@example.org"
    assert item["is_expired"] is False
    assert item["expires_at"]
    assert "token" not in item
    assert "token_hash" not in item


def test_list_invitations_omits_deleted_roles(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    role = admin_authenticated.post(
        "/v1/roles", json={"name": "Temp", "description": "temporary"}
    ).json()
    _invite(mocker, admin_authenticated, role_ids=[2, role["id"]])
    admin_authenticated.delete(f"/v1/roles/{role['id']}")

    [item] = admin_authenticated.get("/v1/invitations").json()
    assert [r["id"] for r in item["roles"]] == [2]


def test_list_invitations_newest_first(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    _invite(mocker, admin_authenticated, email="first@example.org")
    _invite(mocker, admin_authenticated, email="second@example.org")

    emails = [i["email"] for i in admin_authenticated.get("/v1/invitations").json()]
    assert emails == ["second@example.org", "first@example.org"]


def test_list_invitations_flags_expired(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    with patch("src.platform.core.config.settings.invite_expiry", -1):
        _invite(mocker, admin_authenticated)

    [item] = admin_authenticated.get("/v1/invitations").json()
    assert item["is_expired"] is True


def test_list_invitations_is_scoped_to_active_org(
    mocker: MockerFixture,
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    _invite(mocker, admin_authenticated, email="org1@example.org")
    _invite(
        mocker,
        organization2_admin_authenticated,
        email="org2@example.org",
        role_ids=[4],
    )

    org1 = [i["email"] for i in admin_authenticated.get("/v1/invitations").json()]
    org2 = [
        i["email"]
        for i in organization2_admin_authenticated.get("/v1/invitations").json()
    ]
    assert org1 == ["org1@example.org"]
    assert org2 == ["org2@example.org"]


def test_accepted_invitation_is_no_longer_listed(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    token = _invite(mocker, admin_authenticated)
    with TestClient(app) as invitee:
        rs = invitee.post(
            "/v1/auth/complete-invite",
            json={"invite_token": token, "name": "Invited", "password": "password1"},
        )
    assert rs.status_code == 201
    assert admin_authenticated.get("/v1/invitations").json() == []


def test_list_invitations_requires_permission(
    standard_authenticated: TestClient,
) -> None:
    rs = standard_authenticated.get("/v1/invitations")
    assert rs.status_code == 403


def test_list_invitations_requires_authentication(client: TestClient) -> None:
    assert client.get("/v1/invitations").status_code == 401


# --- DELETE /invitations/{id} -----------------------------------------------


def test_revoke_invitation(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    token = _invite(mocker, admin_authenticated)
    [item] = admin_authenticated.get("/v1/invitations").json()

    rs = admin_authenticated.delete(f"/v1/invitations/{item['id']}")
    assert rs.status_code == 204
    assert admin_authenticated.get("/v1/invitations").json() == []

    # The link stops working immediately.
    with TestClient(app) as invitee:
        rs = invitee.post("/v1/auth/invite-status", json={"token": token})
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "invite_invalid"


def test_revoke_invitation_is_audited(
    mocker: MockerFixture, admin_authenticated: TestClient
) -> None:
    _invite(mocker, admin_authenticated)
    [item] = admin_authenticated.get("/v1/invitations").json()
    admin_authenticated.delete(f"/v1/invitations/{item['id']}")

    logs = admin_authenticated.get("/v1/audit-logs").json()["items"]
    [entry] = [e for e in logs if e["action"] == "user.invite_revoke"]
    assert entry["resource_id"] == item["id"]
    assert entry["details"]["email"] == "invited@example.org"


def test_revoke_only_affects_that_orgs_invitation(
    mocker: MockerFixture,
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    email = "shared@example.org"
    _invite(mocker, admin_authenticated, email=email)
    token_org2 = _invite(
        mocker, organization2_admin_authenticated, email=email, role_ids=[4]
    )

    [item] = admin_authenticated.get("/v1/invitations").json()
    admin_authenticated.delete(f"/v1/invitations/{item['id']}")

    with TestClient(app) as invitee:
        rs = invitee.post("/v1/auth/invite-status", json={"token": token_org2})
    assert rs.status_code == 200


def test_cannot_revoke_other_orgs_invitation(
    mocker: MockerFixture,
    admin_authenticated: TestClient,
    organization2_admin_authenticated: TestClient,
) -> None:
    token = _invite(
        mocker,
        organization2_admin_authenticated,
        email="org2@example.org",
        role_ids=[4],
    )
    [item] = organization2_admin_authenticated.get("/v1/invitations").json()

    rs = admin_authenticated.delete(f"/v1/invitations/{item['id']}")
    assert rs.status_code == 404

    with TestClient(app) as invitee:
        rs = invitee.post("/v1/auth/invite-status", json={"token": token})
    assert rs.status_code == 200


def test_revoke_unknown_invitation(admin_authenticated: TestClient) -> None:
    assert admin_authenticated.delete("/v1/invitations/9999").status_code == 404


def test_revoke_invitation_requires_permission(
    standard_authenticated: TestClient,
) -> None:
    rs = standard_authenticated.delete("/v1/invitations/1")
    assert rs.status_code == 403
