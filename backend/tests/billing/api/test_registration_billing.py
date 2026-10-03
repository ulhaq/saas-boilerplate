"""Registration opens a billing account for the new organization."""

from fastapi.testclient import TestClient
from pytest_mock import MockerFixture


def _do_register(client: TestClient, email: str = "new_user@example.org") -> None:
    client.post("/v1/auth/register", json={"email": email, "terms_accepted": True})


def _do_verify(
    mocker: MockerFixture,
    client: TestClient,
    email: str = "new_user@example.org",
) -> str:
    """Register, capture verification token, verify email, return setup_token."""
    mock_send = mocker.patch("src.platform.services.auth.registration.send_email")
    _do_register(client, email)
    verify_url = mock_send.call_args.kwargs["data"]["verify_url"]
    token = verify_url.split("token=")[1]
    mock_send.stop()

    rs = client.post("/v1/auth/verify-email", json={"token": token}).json()
    return rs["setup_token"]


def _do_complete(
    mocker: MockerFixture,
    client: TestClient,
    email: str = "new_user@example.org",
    name: str = "New User",
    password: str = "password1",
) -> dict:
    """Full registration flow - returns the Token response JSON."""
    setup_token = _do_verify(mocker, client, email)
    response = client.post(
        "/v1/auth/complete-registration",
        json={
            "setup_token": setup_token,
            "name": name,
            "password": password,
        },
    )
    return response.json()


def test_registration_seeds_billing_email_from_owner(
    mocker: MockerFixture,
    client: TestClient,
) -> None:
    token_data = _do_complete(mocker, client, password="password1")
    access_token = token_data["access_token"]

    response = client.get(
        "/v1/billing/subscriptions/current",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    assert response.status_code == 200
    assert response.json()["billing_email"] == "new_user@example.org"
