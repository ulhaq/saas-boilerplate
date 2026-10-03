import pytest
from fastapi.testclient import TestClient

from src.foundation.core.config import settings
from src.main import API_CSP, DOCS_CSP

BASE_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
}


def _assert_single(response, name: str, value: str) -> None:
    assert response.headers.get_list(name) == [value], name


@pytest.mark.parametrize(
    ("method", "path", "status"),
    [
        ("GET", "/health", 200),
        ("GET", "/v1/no-such-route", 404),
        ("POST", "/v1/auth/register", 422),
    ],
)
def test_base_security_headers_on_every_response(
    client: TestClient,
    method: str,
    path: str,
    status: int,
) -> None:
    response = client.request(method, path, json={})
    assert response.status_code == status
    for name, value in BASE_HEADERS.items():
        _assert_single(response, name, value)


def test_no_hsts_or_csp_locally(client: TestClient) -> None:
    response = client.get("/health")
    assert "strict-transport-security" not in response.headers
    assert "content-security-policy" not in response.headers


def test_hsts_and_api_csp_outside_local(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    response = client.get("/health")
    _assert_single(
        response,
        "strict-transport-security",
        "max-age=31536000; includeSubDomains",
    )
    _assert_single(response, "content-security-policy", API_CSP)
    for name, value in BASE_HEADERS.items():
        _assert_single(response, name, value)


def test_docs_get_their_own_csp(
    client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(settings, "app_env", "production")
    response = client.get("/docs")
    assert response.status_code == 200
    _assert_single(response, "content-security-policy", DOCS_CSP)
