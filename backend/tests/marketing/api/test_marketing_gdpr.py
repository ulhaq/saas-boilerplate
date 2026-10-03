"""Marketing's share of a user's data export: their waitlist sign-up."""

from fastapi.testclient import TestClient


def test_the_export_includes_the_users_waitlist_sign_up(
    admin_authenticated: TestClient,
):
    export = admin_authenticated.get("/v1/users/me/export").json()
    assert export["modules"]["marketing"] == {"waitlist": None}

    joined = admin_authenticated.post(
        "/v1/waitlist",
        json={"email": "admin@example.org", "name": "Alice"},
    )
    assert joined.status_code == 201

    waitlist = admin_authenticated.get("/v1/users/me/export").json()["modules"][
        "marketing"
    ]["waitlist"]
    assert (waitlist["email"], waitlist["name"]) == ("admin@example.org", "Alice")
