import hashlib
import secrets
from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from httpx import Headers, Response
from sqlalchemy import delete, select

from src.main import app
from src.platform.models.api_token import ApiToken
from src.platform.models.billing import PlanFeature as PlanFeatureModel
from tests.conftest import TestSessionLocal

# ── helpers ──────────────────────────────────────────────────────────────────


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


# ── CRUD ─────────────────────────────────────────────────────────────────────


def test_create_token(admin_authenticated: TestClient) -> None:
    rs = _create_token(admin_authenticated, "my token")
    assert rs.status_code == 201
    data = rs.json()
    assert data["name"] == "my token"
    assert data["token"].startswith("sk_")
    assert len(data["token_prefix"]) == 8
    assert data["expires_at"] is None
    assert data["is_expired"] is False
    assert data["revoked_at"] is None
    assert data["permissions"] == ["manage:api_token"]


def test_create_token_with_expiry(admin_authenticated: TestClient) -> None:
    future = (datetime.now(UTC) + timedelta(days=30)).isoformat()
    rs = _create_token(admin_authenticated, "expiring token", expires_at=future)
    assert rs.status_code == 201
    assert rs.json()["expires_at"] is not None


def test_create_token_with_past_expiry_rejected(
    admin_authenticated: TestClient,
) -> None:
    past = (datetime.now(UTC) - timedelta(seconds=1)).isoformat()
    rs = _create_token(admin_authenticated, "bad token", expires_at=past)
    assert rs.status_code == 422


def test_list_tokens(admin_authenticated: TestClient) -> None:
    _create_token(admin_authenticated, "token a")
    _create_token(admin_authenticated, "token b")
    rs = admin_authenticated.get("/v1/api-tokens")
    assert rs.status_code == 200
    assert len(rs.json()) == 2


def test_list_tokens_excludes_revoked(admin_authenticated: TestClient) -> None:
    token_id = _create_token(admin_authenticated, "keep").json()["id"]
    revoke_id = _create_token(admin_authenticated, "revoke me").json()["id"]
    admin_authenticated.delete(f"/v1/api-tokens/{revoke_id}")
    rs = admin_authenticated.get("/v1/api-tokens")
    ids = [t["id"] for t in rs.json()]
    assert token_id in ids
    assert revoke_id not in ids


def test_revoke_token(admin_authenticated: TestClient) -> None:
    token_id = _create_token(admin_authenticated, "to revoke").json()["id"]
    rs = admin_authenticated.delete(f"/v1/api-tokens/{token_id}")
    assert rs.status_code == 204


def test_revoke_nonexistent_token_returns_404(admin_authenticated: TestClient) -> None:
    rs = admin_authenticated.delete("/v1/api-tokens/99999")
    assert rs.status_code == 404


def test_cannot_manage_tokens_without_permission(
    no_roles_authenticated: TestClient,
) -> None:
    rs = no_roles_authenticated.get("/v1/api-tokens")
    assert rs.status_code == 403


# ── plan feature guard ────────────────────────────────────────────────────────


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


# ── authentication ────────────────────────────────────────────────────────────


def test_authenticate_with_api_token(
    client: TestClient, admin_authenticated: TestClient
) -> None:
    plaintext = _create_token(admin_authenticated, "auth token").json()["token"]
    rs = _api_token_client(client, plaintext).get("/v1/users/me")
    assert rs.status_code == 200
    assert rs.json()["email"] == "admin@example.org"


def test_revoked_token_rejected(
    client: TestClient, admin_authenticated: TestClient
) -> None:
    created = _create_token(admin_authenticated, "to revoke").json()
    admin_authenticated.delete(f"/v1/api-tokens/{created['id']}")
    rs = _api_token_client(client, created["token"]).get("/v1/users/me")
    assert rs.status_code == 401


async def test_expired_token_rejected(client: TestClient) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    _, plaintext = await _seed_token(user_id=1, organization_id=1, expires_at=past)
    rs = _api_token_client(client, plaintext).get("/v1/users/me")
    assert rs.status_code == 401
    assert rs.json()["error_code"] == "token_expired"


def test_invalid_token_rejected(client: TestClient) -> None:
    rs = _api_token_client(client, "sk_totallyinvalid").get("/v1/users/me")
    assert rs.status_code == 401


async def test_auth_blocked_without_api_access_feature(client: TestClient) -> None:
    _, plaintext = await _seed_token(user_id=1, organization_id=1)
    await _remove_api_access_feature()
    rs = _api_token_client(client, plaintext).get("/v1/users/me")
    assert rs.status_code == 402
    assert rs.json()["error_code"] == "plan_feature_unavailable"


# ── is_expired computed field ─────────────────────────────────────────────────


async def test_is_expired_false_for_active_token(
    admin_authenticated: TestClient,
) -> None:
    future = (datetime.now(UTC) + timedelta(days=1)).isoformat()
    data = _create_token(admin_authenticated, "active", expires_at=future).json()
    assert data["is_expired"] is False


async def test_is_expired_true_for_past_expiry(admin_authenticated: TestClient) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    _, _plaintext = await _seed_token(
        user_id=1, organization_id=1, name="expired", expires_at=past
    )
    # Use the plaintext to look up the token via list (seeded tokens appear in list)
    tokens = admin_authenticated.get("/v1/api-tokens").json()
    expired = next(t for t in tokens if t["name"] == "expired")
    assert expired["is_expired"] is True


# ── user removal revokes tokens ───────────────────────────────────────────────


async def test_removing_user_from_org_revokes_tokens(
    admin_authenticated: TestClient,
) -> None:
    _, plaintext = await _seed_token(
        user_id=2, organization_id=1, name="standard token"
    )

    # Token works before removal
    with TestClient(app) as c:
        assert _api_token_client(c, plaintext).get("/v1/users/me").status_code == 200

    # Admin removes standard user from org 1
    rs = admin_authenticated.delete("/v1/users/2")
    assert rs.status_code == 204

    # Token now rejected
    with TestClient(app) as c:
        assert _api_token_client(c, plaintext).get("/v1/users/me").status_code == 401


async def test_tokens_in_other_orgs_unaffected_on_removal(
    client: TestClient, admin_authenticated: TestClient
) -> None:
    """Removing user from org 1 must not revoke their tokens in org 2."""
    # Seed tokens for user 2 in both orgs; assert revoke is scoped to org 1 only.
    _, _plaintext_org2 = await _seed_token(
        user_id=2, organization_id=2, name="org2 token"
    )
    _, _plaintext_org1 = await _seed_token(
        user_id=2, organization_id=1, name="org1 token"
    )

    # Remove user 2 from org 1
    admin_authenticated.delete("/v1/users/2")

    # Org 1 token is revoked
    tokens_org1 = admin_authenticated.get("/v1/api-tokens").json()
    org1_token = next((t for t in tokens_org1 if t["name"] == "org1 token"), None)
    assert org1_token is None  # revoked so excluded from list

    # Org 2 token is untouched (check via DB directly)
    async with TestSessionLocal() as session:
        result = await session.execute(
            select(ApiToken).where(ApiToken.name == "org2 token")
        )
        token = result.scalar_one()
        assert token.revoked_at is None
