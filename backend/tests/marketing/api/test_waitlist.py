from fastapi.testclient import TestClient


def test_join_waitlist(client: TestClient) -> None:
    response = client.post(
        "/v1/waitlist", json={"email": "lead@example.org", "name": "Lead"}
    )
    assert response.status_code == 201
    assert "message" in response.json()


def test_join_waitlist_name_optional(client: TestClient) -> None:
    response = client.post("/v1/waitlist", json={"email": "noname@example.org"})
    assert response.status_code == 201


def test_join_waitlist_is_idempotent(client: TestClient) -> None:
    payload = {"email": "dupe@example.org"}
    first = client.post("/v1/waitlist", json=payload)
    second = client.post("/v1/waitlist", json=payload)
    assert first.status_code == 201
    assert second.status_code == 201


def test_join_waitlist_rejects_invalid_email(client: TestClient) -> None:
    response = client.post("/v1/waitlist", json={"email": "not-an-email"})
    assert response.status_code == 422
