from collections.abc import Generator
from types import SimpleNamespace
from unittest.mock import patch

import pyotp
import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture

import src.platform.core.mfa as mfa_module
from src.main import app
from src.platform.core.config import settings
from tests.utils import advance_clock

ADMIN = {"username": "admin@example.org", "password": "password"}
FORM = {"Content-Type": "application/x-www-form-urlencoded"}


class _Clock:
    """Controls the time the TOTP verifier sees, so tests can step through
    30-second windows deterministically (codes are single-use per step)."""

    def __init__(self) -> None:
        self.now = 1_800_000_000

    def tick(self) -> None:
        self.now += 30

    def code(self, secret: str) -> str:
        return pyotp.TOTP(secret).at(self.now)


@pytest.fixture(autouse=True)
def mfa_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "mfa_enabled", True)


@pytest.fixture
def clock(mocker: MockerFixture) -> _Clock:
    c = _Clock()
    mocker.patch.object(mfa_module, "time", SimpleNamespace(time=lambda: c.now))
    return c


@pytest.fixture
def fresh_client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


def _login(client: TestClient, creds: dict | None = None):
    return client.post("/v1/auth/token", data=creds or ADMIN, headers=FORM)


def _enroll(client: TestClient, clock: _Clock) -> tuple[str, list[str]]:
    """Enable MFA for the authenticated client; return (secret, recovery codes)."""
    secret = client.post("/v1/users/me/mfa/setup").json()["secret"]
    rs = client.post("/v1/users/me/mfa/enable", json={"code": clock.code(secret)})
    assert rs.status_code == 200, rs.text
    clock.tick()
    return secret, rs.json()["recovery_codes"]


# --- enrollment -------------------------------------------------------------


def test_setup_returns_secret_and_otpauth_uri(admin_authenticated: TestClient) -> None:
    rs = admin_authenticated.post("/v1/users/me/mfa/setup")
    assert rs.status_code == 200
    body = rs.json()
    assert body["secret"]
    assert body["otpauth_uri"].startswith("otpauth://totp/")
    assert "admin%40example.org" in body["otpauth_uri"]


def test_setup_does_not_enable_mfa(admin_authenticated: TestClient) -> None:
    admin_authenticated.post("/v1/users/me/mfa/setup")
    assert admin_authenticated.get("/v1/users/me").json()["mfa_enabled"] is False
    assert "access_token" in _login(admin_authenticated).json()


def test_enable_mfa(admin_authenticated: TestClient, clock: _Clock) -> None:
    _, codes = _enroll(admin_authenticated, clock)
    assert len(codes) == settings.mfa_recovery_code_count
    assert len(set(codes)) == len(codes)
    assert admin_authenticated.get("/v1/users/me").json()["mfa_enabled"] is True


def test_enable_mfa_rejects_wrong_code(
    admin_authenticated: TestClient, clock: _Clock
) -> None:
    admin_authenticated.post("/v1/users/me/mfa/setup")
    rs = admin_authenticated.post("/v1/users/me/mfa/enable", json={"code": "000000"})
    assert rs.status_code == 422
    assert rs.json()["error_code"] == "mfa_code_invalid"
    assert admin_authenticated.get("/v1/users/me").json()["mfa_enabled"] is False


def test_enable_mfa_requires_setup_first(admin_authenticated: TestClient) -> None:
    rs = admin_authenticated.post("/v1/users/me/mfa/enable", json={"code": "123456"})
    assert rs.status_code == 422
    assert rs.json()["error_code"] == "mfa_setup_required"


def test_cannot_setup_when_already_enabled(
    admin_authenticated: TestClient, clock: _Clock
) -> None:
    _enroll(admin_authenticated, clock)
    rs = admin_authenticated.post("/v1/users/me/mfa/setup")
    assert rs.status_code == 409
    assert rs.json()["error_code"] == "mfa_already_enabled"


def test_mfa_endpoints_require_authentication(client: TestClient) -> None:
    assert client.post("/v1/users/me/mfa/setup").status_code == 401


# --- login ------------------------------------------------------------------


def test_login_returns_challenge_when_mfa_enabled(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    _enroll(admin_authenticated, clock)

    rs = _login(fresh_client)
    assert rs.status_code == 200
    body = rs.json()
    assert body["mfa_required"] is True
    assert body["mfa_token"]
    assert "access_token" not in body
    assert "refresh_token" not in rs.cookies


def test_verify_mfa_issues_session(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)
    mfa_token = _login(fresh_client).json()["mfa_token"]

    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": clock.code(secret)}
    )
    assert rs.status_code == 200
    assert rs.json()["access_token"]
    assert "refresh_token" in rs.cookies

    me = fresh_client.get(
        "/v1/users/me",
        headers={"Authorization": f"Bearer {rs.json()['access_token']}"},
    )
    assert me.json()["email"] == "admin@example.org"


def test_verify_mfa_rejects_wrong_code(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    _enroll(admin_authenticated, clock)
    mfa_token = _login(fresh_client).json()["mfa_token"]

    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "000000"}
    )
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "mfa_code_invalid"


def test_totp_code_cannot_be_replayed(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)
    code = clock.code(secret)

    token1 = _login(fresh_client).json()["mfa_token"]
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": token1, "code": code}
    )
    assert rs.status_code == 200

    token2 = _login(fresh_client).json()["mfa_token"]
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": token2, "code": code}
    )
    assert rs.status_code == 401


def test_totp_accepts_adjacent_step_for_clock_drift(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)
    code = clock.code(secret)
    clock.tick()  # server clock is one step ahead of the authenticator

    mfa_token = _login(fresh_client).json()["mfa_token"]
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": code}
    )
    assert rs.status_code == 200


def test_recovery_code_logs_in_once(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    _, codes = _enroll(admin_authenticated, clock)

    mfa_token = _login(fresh_client).json()["mfa_token"]
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": codes[0]}
    )
    assert rs.status_code == 200

    mfa_token = _login(fresh_client).json()["mfa_token"]
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": codes[0]}
    )
    assert rs.status_code == 401


def test_recovery_code_is_case_and_dash_insensitive(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    _, codes = _enroll(admin_authenticated, clock)
    mfa_token = _login(fresh_client).json()["mfa_token"]
    rs = fresh_client.post(
        "/v1/auth/mfa/verify",
        json={"mfa_token": mfa_token, "code": codes[1].replace("-", "").upper()},
    )
    assert rs.status_code == 200


def test_verify_mfa_locks_after_repeated_failures(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)
    mfa_token = _login(fresh_client).json()["mfa_token"]

    for _ in range(settings.mfa_max_failed_attempts):
        rs = fresh_client.post(
            "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": "000000"}
        )
        assert rs.json()["error_code"] == "mfa_code_invalid"

    # Even the correct code is refused while locked.
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": clock.code(secret)}
    )
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "mfa_locked"

    with advance_clock(
        "src.platform.services.auth", seconds=settings.mfa_lockout_seconds + 1
    ):
        rs = fresh_client.post(
            "/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": clock.code(secret)},
        )
    assert rs.status_code == 200


def test_verify_mfa_rejects_tampered_token(fresh_client: TestClient) -> None:
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": "garbage", "code": "123456"}
    )
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "signature_invalid"


def test_verify_mfa_rejects_expired_token(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)
    mfa_token = _login(fresh_client).json()["mfa_token"]

    with patch.object(settings, "mfa_challenge_expiry", -1):
        rs = fresh_client.post(
            "/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": clock.code(secret)},
        )
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "signature_expired"


# --- managing MFA -----------------------------------------------------------


def test_disable_mfa(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)

    rs = admin_authenticated.post(
        "/v1/users/me/mfa/disable",
        json={"password": "password", "code": clock.code(secret)},
    )
    assert rs.status_code == 204
    assert admin_authenticated.get("/v1/users/me").json()["mfa_enabled"] is False
    assert "access_token" in _login(fresh_client).json()


def test_disable_mfa_with_recovery_code(
    admin_authenticated: TestClient, clock: _Clock
) -> None:
    _, codes = _enroll(admin_authenticated, clock)
    rs = admin_authenticated.post(
        "/v1/users/me/mfa/disable", json={"password": "password", "code": codes[0]}
    )
    assert rs.status_code == 204


def test_disable_mfa_requires_password(
    admin_authenticated: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)
    rs = admin_authenticated.post(
        "/v1/users/me/mfa/disable",
        json={"password": "wrong", "code": clock.code(secret)},
    )
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "login_failed"
    assert admin_authenticated.get("/v1/users/me").json()["mfa_enabled"] is True


def test_disable_mfa_requires_valid_code(
    admin_authenticated: TestClient, clock: _Clock
) -> None:
    _enroll(admin_authenticated, clock)
    rs = admin_authenticated.post(
        "/v1/users/me/mfa/disable", json={"password": "password", "code": "000000"}
    )
    assert rs.status_code == 422
    assert admin_authenticated.get("/v1/users/me").json()["mfa_enabled"] is True


def test_regenerate_recovery_codes_invalidates_old_ones(
    admin_authenticated: TestClient, fresh_client: TestClient, clock: _Clock
) -> None:
    secret, old_codes = _enroll(admin_authenticated, clock)

    rs = admin_authenticated.post(
        "/v1/users/me/mfa/recovery-codes", json={"code": clock.code(secret)}
    )
    assert rs.status_code == 200
    new_codes = rs.json()["recovery_codes"]
    assert set(new_codes).isdisjoint(old_codes)

    mfa_token = _login(fresh_client).json()["mfa_token"]
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": old_codes[0]}
    )
    assert rs.status_code == 401
    rs = fresh_client.post(
        "/v1/auth/mfa/verify", json={"mfa_token": mfa_token, "code": new_codes[0]}
    )
    assert rs.status_code == 200


def test_mfa_actions_are_audited(
    admin_authenticated: TestClient, clock: _Clock
) -> None:
    secret, _ = _enroll(admin_authenticated, clock)
    admin_authenticated.post(
        "/v1/users/me/mfa/disable",
        json={"password": "password", "code": clock.code(secret)},
    )
    actions = {
        item["action"]
        for item in admin_authenticated.get("/v1/audit-logs").json()["items"]
    }
    assert {"user.mfa_enable", "user.mfa_disable"} <= actions


# --- invites ----------------------------------------------------------------


def test_existing_mfa_user_must_complete_sign_in_to_accept_invite(
    mocker: MockerFixture, clock: _Clock
) -> None:
    with TestClient(app) as invitee, TestClient(app) as admin:
        # admin2 (Org 2) enrolls in MFA.
        rs = _login(invitee, {"username": "admin2@example.org", "password": "password"})
        invitee.headers["Authorization"] = f"Bearer {rs.json()['access_token']}"
        secret, _ = _enroll(invitee, clock)
        invitee.headers.pop("Authorization")
        invitee.cookies.clear()

        # admin (Org 1) invites admin2.
        rs = _login(admin)
        admin.headers["Authorization"] = f"Bearer {rs.json()['access_token']}"
        mock_send = mocker.patch("src.platform.services.user.send_email")
        admin.post(
            "/v1/users/invite", json={"email": "admin2@example.org", "role_ids": [2]}
        )
        invite_token = mock_send.call_args.kwargs["data"]["invite_url"].split("token=")[
            1
        ]
        mocker.patch("src.platform.services.auth.send_email")

        # The invite link alone neither signs in nor joins the org.
        rs = invitee.post(
            "/v1/auth/complete-invite", json={"invite_token": invite_token}
        )
        assert rs.status_code == 403
        assert rs.json()["error_code"] == "invite_login_required"
        members = admin.get("/v1/organizations/1/users").json()["items"]
        assert "admin2@example.org" not in {m["email"] for m in members}

        # Password alone isn't a session either; the code is required.
        mfa_token = _login(
            invitee, {"username": "admin2@example.org", "password": "password"}
        ).json()["mfa_token"]
        rs = invitee.post(
            "/v1/auth/accept-invite",
            json={"invite_token": invite_token},
            headers={"Authorization": f"Bearer {mfa_token}"},
        )
        assert rs.status_code == 401

        # Full sign-in, then accept.
        rs = invitee.post(
            "/v1/auth/mfa/verify",
            json={"mfa_token": mfa_token, "code": clock.code(secret)},
        )
        invitee.headers["Authorization"] = f"Bearer {rs.json()['access_token']}"
        rs = invitee.post("/v1/auth/accept-invite", json={"invite_token": invite_token})
        assert rs.status_code == 201
        members = admin.get("/v1/organizations/1/users").json()["items"]
        assert "admin2@example.org" in {m["email"] for m in members}


# --- feature flag -----------------------------------------------------------


def test_mfa_endpoints_404_when_flag_off(
    admin_authenticated: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(settings, "mfa_enabled", False)
    assert admin_authenticated.post("/v1/users/me/mfa/setup").status_code == 404
    rs = admin_authenticated.post(
        "/v1/auth/mfa/verify", json={"mfa_token": "x", "code": "123456"}
    )
    assert rs.status_code == 404


def test_enrolled_user_logs_in_without_code_when_flag_off(
    admin_authenticated: TestClient,
    fresh_client: TestClient,
    clock: _Clock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _enroll(admin_authenticated, clock)
    monkeypatch.setattr(settings, "mfa_enabled", False)
    assert "access_token" in _login(fresh_client).json()
