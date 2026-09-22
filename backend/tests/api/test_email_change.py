from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy import select

import src.platform.core.mfa as mfa_module
from src.main import app
from src.platform.core.config import settings
from src.platform.models.audit_log import AuditLog
from tests.api.test_mfa import _Clock, _enroll
from tests.conftest import TestSessionLocal

FORM = {"Content-Type": "application/x-www-form-urlencoded"}
NEW_EMAIL = "admin.new@example.org"


@pytest.fixture
def user_mail(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("src.platform.services.user.send_email")


@pytest.fixture
def auth_mail(mocker: MockerFixture) -> MagicMock:
    return mocker.patch("src.platform.services.auth.send_email")


@pytest.fixture
def clock(mocker: MockerFixture) -> _Clock:
    c = _Clock()
    mocker.patch.object(mfa_module, "time", SimpleNamespace(time=lambda: c.now))
    return c


def _request(client: TestClient, **overrides):
    body = {"new_email": NEW_EMAIL, "password": "password", **overrides}
    return client.post("/v1/users/me/email", json=body)


def _confirm_token(user_mail: MagicMock) -> str:
    [call] = [
        c
        for c in user_mail.call_args_list
        if c.kwargs["email_template"] == "verify-email-change"
    ]
    return call.kwargs["data"]["confirm_url"].split("token=")[1]


def _login(email: str, password: str = "password"):
    with TestClient(app) as c:
        return c.post(
            "/v1/auth/token",
            data={"username": email, "password": password},
            headers=FORM,
        )


# --- request ----------------------------------------------------------------


def test_request_sends_confirmation_and_notice(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    rs = _request(admin_authenticated)
    assert rs.status_code == 202

    sent = {c.kwargs["email_template"]: c.kwargs for c in user_mail.call_args_list}
    assert sent["verify-email-change"]["address"] == NEW_EMAIL
    assert (
        "/confirm-email-change?token="
        in (sent["verify-email-change"]["data"]["confirm_url"])
    )
    assert sent["email-change-requested"]["address"] == "admin@example.org"
    assert sent["email-change-requested"]["data"]["new_email"] == NEW_EMAIL


def test_request_does_not_change_email_yet(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    _request(admin_authenticated)
    assert admin_authenticated.get("/v1/users/me").json()["email"] == (
        "admin@example.org"
    )


def test_request_requires_correct_password(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    rs = _request(admin_authenticated, password="wrong")
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "login_failed"
    user_mail.assert_not_called()


def test_request_rejects_same_email(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    rs = _request(admin_authenticated, new_email="ADMIN@example.org")
    assert rs.status_code == 422
    assert rs.json()["error_code"] == "email_unchanged"


def test_request_rejects_taken_email(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    rs = _request(admin_authenticated, new_email="standard@example.org")
    assert rs.status_code == 409
    assert rs.json()["error_code"] == "email_already_exists"
    user_mail.assert_not_called()


def test_request_rejects_disposable_email(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    rs = _request(admin_authenticated, new_email="user@mailinator.com")
    assert rs.status_code == 422


def test_request_requires_authentication(client: TestClient) -> None:
    assert _request(client).status_code == 401


def test_request_is_audited(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    _request(admin_authenticated)
    logs = admin_authenticated.get("/v1/audit-logs").json()["items"]
    [entry] = [e for e in logs if e["action"] == "user.email_change_request"]
    assert entry["details"]["new_email"] == NEW_EMAIL


# --- request with two-factor auth -------------------------------------------


@pytest.fixture
def mfa_admin(
    admin_authenticated: TestClient, clock: _Clock, monkeypatch: pytest.MonkeyPatch
) -> tuple[TestClient, str, list[str]]:
    monkeypatch.setattr(settings, "mfa_enabled", True)
    secret, codes = _enroll(admin_authenticated, clock)
    return admin_authenticated, secret, codes


def test_request_with_mfa_requires_code(
    mfa_admin: tuple[TestClient, str, list[str]], user_mail: MagicMock
) -> None:
    client, _, _ = mfa_admin
    rs = _request(client)
    assert rs.status_code == 422
    assert rs.json()["error_code"] == "mfa_code_required"
    user_mail.assert_not_called()


def test_request_with_mfa_rejects_wrong_code(
    mfa_admin: tuple[TestClient, str, list[str]], user_mail: MagicMock
) -> None:
    client, _, _ = mfa_admin
    rs = _request(client, code="000000")
    assert rs.status_code == 422
    assert rs.json()["error_code"] == "mfa_code_invalid"
    user_mail.assert_not_called()


def test_request_with_mfa_accepts_totp_code(
    mfa_admin: tuple[TestClient, str, list[str]], clock: _Clock, user_mail: MagicMock
) -> None:
    client, secret, _ = mfa_admin
    assert _request(client, code=clock.code(secret)).status_code == 202


def test_request_with_mfa_accepts_recovery_code(
    mfa_admin: tuple[TestClient, str, list[str]], user_mail: MagicMock
) -> None:
    client, _, codes = mfa_admin
    assert _request(client, code=codes[0]).status_code == 202


def test_request_skips_code_when_mfa_flag_off(
    mfa_admin: tuple[TestClient, str, list[str]],
    user_mail: MagicMock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    client, _, _ = mfa_admin
    monkeypatch.setattr(settings, "mfa_enabled", False)
    assert _request(client).status_code == 202


# --- confirm ----------------------------------------------------------------


def test_confirm_changes_email(
    admin_authenticated: TestClient, user_mail: MagicMock, auth_mail: MagicMock
) -> None:
    _request(admin_authenticated)
    token = _confirm_token(user_mail)

    with TestClient(app) as anonymous:
        rs = anonymous.post("/v1/auth/confirm-email-change", json={"token": token})
    assert rs.status_code == 204

    assert "access_token" in _login(NEW_EMAIL).json()
    assert _login("admin@example.org").status_code == 401

    auth_mail.assert_called_once()
    assert auth_mail.call_args.kwargs["email_template"] == "email-changed"
    assert auth_mail.call_args.kwargs["address"] == "admin@example.org"
    assert auth_mail.call_args.kwargs["data"]["new_email"] == NEW_EMAIL


def test_confirm_signs_out_all_sessions(
    admin_authenticated: TestClient, user_mail: MagicMock, auth_mail: MagicMock
) -> None:
    # admin_authenticated's login set a refresh cookie on this client.
    assert admin_authenticated.post("/v1/auth/refresh").status_code == 200

    _request(admin_authenticated)
    with TestClient(app) as anonymous:
        anonymous.post(
            "/v1/auth/confirm-email-change", json={"token": _confirm_token(user_mail)}
        )

    assert admin_authenticated.post("/v1/auth/refresh").status_code == 401


async def test_confirm_is_audited(
    admin_authenticated: TestClient, user_mail: MagicMock, auth_mail: MagicMock
) -> None:
    _request(admin_authenticated)
    with TestClient(app) as anonymous:
        anonymous.post(
            "/v1/auth/confirm-email-change", json={"token": _confirm_token(user_mail)}
        )

    # User-level event (no org context when the link is clicked), like
    # auth.password_reset - so it isn't in any org's audit-log listing.
    async with TestSessionLocal() as session:
        rs = await session.execute(
            select(AuditLog).where(AuditLog.action == "user.email_change")
        )
        [entry] = rs.scalars().all()
    assert entry.user_id == 1
    assert entry.details == {"old_email": "admin@example.org", "new_email": NEW_EMAIL}


def test_confirm_link_works_once(
    admin_authenticated: TestClient, user_mail: MagicMock, auth_mail: MagicMock
) -> None:
    _request(admin_authenticated)
    token = _confirm_token(user_mail)
    with TestClient(app) as anonymous:
        anonymous.post("/v1/auth/confirm-email-change", json={"token": token})
        rs = anonymous.post("/v1/auth/confirm-email-change", json={"token": token})
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "token_invalid"


def test_confirm_rejects_if_new_email_taken_meanwhile(
    mocker: MockerFixture,
    admin_authenticated: TestClient,
    user_mail: MagicMock,
    auth_mail: MagicMock,
) -> None:
    _request(admin_authenticated, new_email="later@example.org")
    token = _confirm_token(user_mail)

    # Someone registers the address before the link is clicked.
    with TestClient(app) as other:
        other.post(
            "/v1/auth/register",
            json={"email": "later@example.org", "terms_accepted": True},
        )
        setup = other.post(
            "/v1/auth/verify-email",
            json={
                "token": auth_mail.call_args.kwargs["data"]["verify_url"].split(
                    "token="
                )[1]
            },
        ).json()["setup_token"]
        other.post(
            "/v1/auth/complete-registration",
            json={"setup_token": setup, "name": "Later", "password": "password1"},
        )

        rs = other.post("/v1/auth/confirm-email-change", json={"token": token})
    assert rs.status_code == 409
    assert rs.json()["error_code"] == "email_already_exists"
    assert "access_token" in _login("admin@example.org").json()


def test_confirm_rejects_expired_link(
    admin_authenticated: TestClient, user_mail: MagicMock
) -> None:
    _request(admin_authenticated)
    token = _confirm_token(user_mail)
    with (
        patch.object(settings, "email_change_expiry", -1),
        TestClient(app) as anonymous,
    ):
        rs = anonymous.post("/v1/auth/confirm-email-change", json={"token": token})
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "signature_expired"


def test_confirm_rejects_tampered_link(client: TestClient) -> None:
    rs = client.post("/v1/auth/confirm-email-change", json={"token": "garbage"})
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "signature_invalid"
