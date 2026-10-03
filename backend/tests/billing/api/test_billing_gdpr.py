"""Billing's share of a user's data export: organizations billed to them."""

from fastapi.testclient import TestClient

from tests.billing.utils import get_billing_account
from tests.conftest import TestSessionLocal


async def test_the_export_lists_organizations_billed_to_the_user(
    admin_authenticated: TestClient,
):
    # Billing emails match whatever the case.
    async with TestSessionLocal() as session, session.begin():
        account = await get_billing_account(session, 1)
        account.billing_email = "Admin@Example.org"

    export = admin_authenticated.get("/v1/users/me/export").json()

    assert export["modules"]["billing"] == {
        "billed_organizations": [
            {"organization_id": 1, "billing_email": "Admin@Example.org"},
        ],
    }
