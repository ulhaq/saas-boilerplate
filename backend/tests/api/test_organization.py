from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from src.platform.models.organization import Organization
from tests.conftest import TestSessionLocal


async def _seed_external_customer(
    organization_id: int, external_customer_id: str
) -> None:
    async with TestSessionLocal() as session:
        org = await session.get(Organization, organization_id)
        assert org is not None
        org.external_customer_id = external_customer_id
        await session.commit()


def test_user_organizations_list_only_shows_own_organization(
    organization2_admin_authenticated: TestClient,
) -> None:
    response = organization2_admin_authenticated.get("/v1/organizations")
    assert response.status_code == 200
    rs = response.json()
    assert len(rs) == 1
    assert rs[0]["name"] == "Globex Ltd"


def test_create_an_organization(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.post(
        "/v1/organizations",
        json={
            "name": "test organization",
        },
    )
    assert response.status_code == 201
    rs = response.json()
    assert rs["id"] == 3
    assert rs["name"] == "test organization"
    assert rs["created_at"]
    assert rs["updated_at"]

    # Creator should be a member and have owner access
    response = admin_authenticated.get("/v1/organizations/3")
    assert response.status_code == 200

    response = admin_authenticated.get("/v1/organizations/3/users")
    assert response.status_code == 200
    rs = response.json()
    assert rs["total"] == 1
    assert rs["items"][0]["roles"][0]["name"] == "Owner"


def test_cannot_create_an_organization_with_already_existing_name(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.post(
        "/v1/organizations",
        json={
            "name": "Acme Corp",
        },
    )
    assert response.status_code == 409
    rs = response.json()
    assert rs["msg"] == "Organization already exists. [name=Acme Corp]"


def test_create_an_organization_creates_free_subscription(
    admin_authenticated: TestClient,
    mock_billing_provider: MagicMock,
) -> None:
    admin_authenticated.post("/v1/organizations", json={"name": "billed organization"})

    # No Stripe customer is created at registration - deferred to trial or checkout
    mock_billing_provider.get_or_create_customer.assert_not_called()
    # Free plan subscription is local-only - no provider subscription is created
    mock_billing_provider.create_subscription.assert_not_called()


def test_patch_an_organization(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.patch(
        "/v1/organizations/1",
        json={"name": "Patched Organization"},
    )
    assert response.status_code == 200
    rs = response.json()
    assert rs["id"] == 1
    assert rs["name"] == "Patched Organization"
    assert rs["created_at"]
    assert rs["updated_at"]


async def test_patch_organization_name_does_not_sync_to_stripe(
    admin_authenticated: TestClient, mock_billing_provider: MagicMock
) -> None:
    # Org name is an app-only concept; the Stripe customer name is owned by
    # Stripe (set at checkout / editable via the customer portal) and must not
    # be overwritten when the organization is renamed.
    await _seed_external_customer(organization_id=1, external_customer_id="cus_test123")

    response = admin_authenticated.patch(
        "/v1/organizations/1", json={"name": "Renamed Org"}
    )

    assert response.status_code == 200
    mock_billing_provider.update_customer.assert_not_called()


def test_patch_an_organization_with_partial_body(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.patch("/v1/organizations/1", json={})
    assert response.status_code == 200
    rs = response.json()
    assert rs["id"] == 1
    assert rs["name"] == "Acme Corp"


def test_retrieve_an_organization(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/organizations/1")
    assert response.status_code == 200
    rs = response.json()

    assert rs["id"] == 1
    assert rs["name"] == "Acme Corp"
    assert rs["created_at"]
    assert rs["updated_at"]


def test_delete_an_organization(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.delete("/v1/organizations/1")
    assert response.status_code == 204
    # admin is the only member of org 1, so they are soft-deleted along with the org


def test_cannot_access_other_organization(admin_authenticated: TestClient) -> None:
    response = admin_authenticated.get("/v1/organizations/2")
    assert response.status_code == 403

    response = admin_authenticated.patch("/v1/organizations/2", json={"name": "Hacked"})
    assert response.status_code == 403

    response = admin_authenticated.delete("/v1/organizations/2")
    assert response.status_code == 403


def test_cannot_patch_an_organization_while_unauthorized(
    standard_authenticated: TestClient,
) -> None:
    response = standard_authenticated.patch(
        "/v1/organizations/1",
        json={"name": "Patched Organization"},
    )
    assert response.status_code == 403
    rs = response.json()
    assert rs["msg"] == "You are not authorized to perform this action"


def test_cannot_delete_an_organization_while_unauthorized(
    standard_authenticated: TestClient,
) -> None:
    response = standard_authenticated.delete("/v1/organizations/1")
    assert response.status_code == 403
    rs = response.json()
    assert rs["msg"] == "You are not authorized to perform this action"


def test_cannot_remove_owner_from_organization(admin_authenticated: TestClient) -> None:
    # User 1 is the Owner of org 1
    # removing the owner is blocked
    response = admin_authenticated.delete("/v1/users/1")
    assert response.status_code == 403
    rs = response.json()
    assert rs["error_code"] == "owner_removal"


async def test_transfer_ownership_success(
    admin_authenticated: TestClient, mock_billing_provider: MagicMock
) -> None:
    await _seed_external_customer(organization_id=1, external_customer_id="cus_test123")

    # Transfer ownership from user 1 (admin) to user 2 (standard)
    response = admin_authenticated.post(
        "/v1/organizations/1/transfer-ownership", json={"user_id": 2}
    )
    assert response.status_code == 204

    # Stripe customer email updated to new owner's email
    mock_billing_provider.update_customer.assert_called_once_with(
        "cus_test123", email="standard@example.org"
    )

    # Former owner (user 1) no longer has permissions
    # verify via 403 on org users endpoint
    assert admin_authenticated.get("/v1/organizations/1/users").status_code == 403


async def test_transfer_ownership_to_self_rejected(
    admin_authenticated: TestClient,
) -> None:
    response = admin_authenticated.post(
        "/v1/organizations/1/transfer-ownership", json={"user_id": 1}
    )
    assert response.status_code == 403


async def test_transfer_ownership_non_member_rejected(
    admin_authenticated: TestClient,
) -> None:
    # User 4 is in org 2, not org 1
    response = admin_authenticated.post(
        "/v1/organizations/1/transfer-ownership", json={"user_id": 4}
    )
    assert response.status_code == 404


def test_transfer_ownership_requires_owner(standard_authenticated: TestClient) -> None:
    response = standard_authenticated.post(
        "/v1/organizations/1/transfer-ownership", json={"user_id": 3}
    )
    assert response.status_code == 403
