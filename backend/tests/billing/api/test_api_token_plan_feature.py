"""API tokens need the `api_token` plan feature (billing's entitlements)."""

import hashlib
import secrets
from datetime import datetime

from fastapi.testclient import TestClient
from httpx import Headers, Response
from sqlalchemy import delete

from src.billing.models.billing import PlanFeature as PlanFeatureModel
from src.foundation.models.api_token import ApiToken
from tests.conftest import TestSessionLocal


def _create_token(
    client: TestClient,
    name: str = "test token",
    expires_at: str | None = None,
    permissions: list[str] | None = None,
) -> Response:
    payload: dict = {
        "name": name,
        "expires_at": expires_at,
        "permissions": permissions or ["manage:api_token"],
    }
    return client.post("/v1/api-tokens", json=payload)


async def _seed_token(
    user_id: int,
    organization_id: int,
    name: str = "seeded",
    expires_at: datetime | None = None,
) -> tuple[int, str]:
    """Insert an ApiToken row directly and return (token_id, plaintext)."""
    plaintext = "sk_" + secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
    prefix_start = len("sk_")
    token_prefix = plaintext[prefix_start : prefix_start + 8]

    async with TestSessionLocal() as session:
        token = ApiToken(
            user_id=user_id,
            organization_id=organization_id,
            name=name,
            token_hash=token_hash,
            token_prefix=token_prefix,
            permissions=[],
            expires_at=expires_at,
        )
        session.add(token)
        await session.commit()
        await session.refresh(token)
        token_id = token.id

    return token_id, plaintext


def _api_token_client(client: TestClient, plaintext: str) -> TestClient:
    client.headers = Headers({"Authorization": f"Bearer {plaintext}"})
    return client


async def _remove_api_access_feature() -> None:
    async with TestSessionLocal() as session:
        await session.execute(delete(PlanFeatureModel))
        await session.commit()


async def test_list_tokens_blocked_without_api_access_feature(
    admin_authenticated: TestClient,
) -> None:
    await _remove_api_access_feature()
    rs = admin_authenticated.get("/v1/api-tokens")
    assert rs.status_code == 402
    assert rs.json()["error_code"] == "plan_feature_unavailable"


async def test_create_token_blocked_without_api_access_feature(
    admin_authenticated: TestClient,
) -> None:
    await _remove_api_access_feature()
    rs = _create_token(admin_authenticated)
    assert rs.status_code == 402
    assert rs.json()["error_code"] == "plan_feature_unavailable"


async def test_revoke_token_blocked_without_api_access_feature(
    admin_authenticated: TestClient,
) -> None:
    token_id = _create_token(admin_authenticated).json()["id"]
    await _remove_api_access_feature()
    rs = admin_authenticated.delete(f"/v1/api-tokens/{token_id}")
    assert rs.status_code == 402
    assert rs.json()["error_code"] == "plan_feature_unavailable"


async def test_auth_blocked_without_api_access_feature(client: TestClient) -> None:
    _, plaintext = await _seed_token(user_id=1, organization_id=1)
    await _remove_api_access_feature()
    rs = _api_token_client(client, plaintext).get("/v1/users/me")
    assert rs.status_code == 402
    assert rs.json()["error_code"] == "plan_feature_unavailable"
