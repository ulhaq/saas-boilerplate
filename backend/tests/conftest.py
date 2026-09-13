import hashlib
import os
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime

import pytest
import sqlalchemy.dialects.postgresql as _pg_dialect
from fastapi.testclient import TestClient
from httpx import Headers
from sqlalchemy import JSON, StaticPool
from sqlalchemy import text as _text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# These must run before any src imports:
# - env vars are read at import time by config/database modules
# - JSONB→JSON patch lets SQLite run Base.metadata.create_all() in tests
os.environ["RATE_LIMIT_ENABLED"] = "false"
_pg_dialect.JSONB = JSON  # ty: ignore[invalid-assignment]

import src.platform.core.security as _security_mod  # noqa: E402
from src.bootstrap import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS  # noqa: E402
from src.init_db import INIT_AUTH_DATA  # noqa: E402
from src.main import app  # noqa: E402
from src.platform.billing import (  # noqa: E402
    BillingProviderABC,
    CheckoutResult,
    CustomerPortalResult,
    ExternalPrice,
    ExternalProduct,
    ExternalSubscription,
    WebhookPayload,
    get_billing_provider,
)
from src.platform.core.config import settings  # noqa: E402
from src.platform.core.database import Base, get_db  # noqa: E402
from src.platform.core.security import hash_secret  # noqa: E402
from src.platform.enums import PlanFeature  # noqa: E402
from src.platform.models.billing import Plan, PlanPrice, Subscription  # noqa: E402
from src.platform.models.billing import PlanFeature as PlanFeatureModel  # noqa: E402
from src.platform.models.organization import Organization  # noqa: E402
from src.platform.models.permission import Permission  # noqa: E402
from src.platform.models.role import Role  # noqa: E402
from src.platform.models.user import User  # noqa: E402
from src.platform.models.user_organization import UserOrganization  # noqa: E402

TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=StaticPool)
TestSessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=test_engine
)


async def db() -> AsyncGenerator[AsyncSession]:
    async with TestSessionLocal() as session:
        async with session.begin():
            yield session


app.dependency_overrides[get_db] = db


class _FastCryptContext:
    """SHA256-based drop-in for the argon2 context. No key-stretching - tests only."""

    def hash(self, secret: str) -> str:
        return "t$" + hashlib.sha256(secret.encode()).hexdigest()

    def verify(self, plain: str, hashed: str) -> bool:
        return hashed == self.hash(plain)


@pytest.fixture(scope="session", autouse=True)
def allow_multiple_organizations() -> Generator[None]:
    """Force ALLOW_MULTIPLE_ORGANIZATIONS on for tests regardless of .env."""
    original = settings.allow_multiple_organizations
    settings.allow_multiple_organizations = True
    yield
    settings.allow_multiple_organizations = original


@pytest.fixture(scope="session", autouse=True)
def fast_password_hashing() -> Generator[None]:
    original = _security_mod.crypt_context
    _security_mod.crypt_context = _FastCryptContext()  # ty: ignore[invalid-assignment]
    yield
    _security_mod.crypt_context = original


@pytest.fixture(scope="function", autouse=True)
async def prepare_database() -> AsyncGenerator[None]:
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    hashed_password = hash_secret("password")
    async with TestSessionLocal() as session:
        organizations = []
        for organization in INIT_AUTH_DATA["organizations"]:
            organizations.append(
                Organization(
                    name=organization["name"],
                    billing_email=organization["billing_email"],
                )
            )
        session.add_all(organizations)

        permissions = []
        for permission in ALL_PERMISSIONS:
            permissions.append(
                Permission(
                    name=permission.value,
                    description=PERMISSION_DESCRIPTIONS[permission],
                )
            )
        session.add_all(permissions)

        roles = []
        for role in INIT_AUTH_DATA["roles"]:
            roles.append(
                Role(
                    name=role["name"],
                    description=role["description"],
                    is_protected=role.get("is_protected", False),
                    organization=organizations[role["organization"] - 1],
                    permissions=[
                        permission
                        for permission in permissions
                        if permission.name in role["permissions"]
                    ],
                )
            )
        session.add_all(roles)

        users = []
        for user in INIT_AUTH_DATA["users"]:
            users.append(
                User(
                    name=user["name"],
                    email=user["email"],
                    password=hashed_password,
                    roles=[
                        role
                        for idx, role in enumerate(roles, 1)
                        if idx in user["roles"]
                    ],
                )
            )
        session.add_all(users)

        await session.flush()

        user_organizations = []
        for user_data, user in zip(INIT_AUTH_DATA["users"], users, strict=False):
            user_organizations.append(
                UserOrganization(
                    user_id=user.id,
                    organization_id=organizations[user_data["organization"] - 1].id,
                    last_active_at=datetime.now(UTC),
                )
            )
        session.add_all(user_organizations)

        # Seed free plan - local-only, no Stripe product/price IDs
        free_plan = Plan(
            name="Free",
            description="Free plan",
            external_product_id=None,
            is_active=True,
        )
        session.add(free_plan)
        await session.flush()
        free_price = PlanPrice(
            plan_id=free_plan.id,
            amount=0,
            currency="dkk",
            interval="month",
            interval_count=1,
            external_price_id=None,
            is_active=True,
        )
        session.add(free_price)
        await session.flush()
        session.add(
            PlanFeatureModel(plan_id=free_plan.id, feature=PlanFeature.API_TOKEN)
        )
        await session.flush()

        # Seed a free subscription for each test organization, matching what
        # _setup_new_organization does in production. No Stripe customer is created
        # at registration - external_customer_id is set when the organization starts
        # a trial or paid checkout. Tests that need a paid subscription
        # activate it via checkout + webhook helpers (which will stamp the ID).
        for organization in organizations:
            session.add(
                Subscription(
                    organization_id=organization.id,
                    plan_price_id=free_price.id,
                    status="active",
                )
            )

        await session.commit()
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def mock_pg_advisory_lock(mocker):
    """Make pg_advisory_xact_lock a no-op in SQLite tests.

    This is a PostgreSQL-only function used in start_checkout to prevent
    concurrent duplicate customer creation. SQLite does not support it, so
    we replace the one text() call in the billing service with SELECT 1.
    """

    def _patched_text(clause: str):
        if "pg_advisory_xact_lock" in clause:
            return _text("SELECT 1")
        return _text(clause)

    mocker.patch("src.platform.repositories.billing.text", side_effect=_patched_text)


@pytest.fixture(autouse=True)
def mock_send_email(mocker):
    """Prevent real SMTP calls in unit/integration tests."""
    mocker.patch("src.platform.services.billing.send_email")
    mocker.patch("src.platform.services.auth.send_email")
    mocker.patch("src.platform.services.user.send_email")
    mocker.patch("src.platform.services.contact.send_email")
    mocker.patch("src.platform.services.mailer._MAX_EMAIL_ATTEMPTS", 1)


@pytest.fixture(autouse=True)
def mock_billing_provider(mocker):
    """Auto-used fixture that mocks the billing provider for all tests."""
    mock = mocker.MagicMock(spec=BillingProviderABC)

    mock.create_product.return_value = ExternalProduct(external_id="prod_test123")
    mock.update_product.return_value = ExternalProduct(external_id="prod_test123")
    mock.archive_product.return_value = None
    mock.create_price.return_value = ExternalPrice(external_id="price_test123")
    mock.archive_price.return_value = None
    _cus_ids = {1: "cus_test123", 2: "cus_test456"}
    mock.get_or_create_customer.side_effect = lambda *, organization_id, **kw: (
        _cus_ids.get(organization_id, f"cus_{organization_id}")
    )
    mock.create_checkout_session.return_value = CheckoutResult(
        checkout_url="https://checkout.stripe.com/test_session",
        external_session_id="cs_test123",
    )
    mock.cancel_subscription.return_value = ExternalSubscription(
        external_subscription_id="sub_test123",
        external_customer_id="cus_test123",
        status="active",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=True,
        canceled_at=None,
        external_price_id="price_test123",
    )
    mock.resume_subscription.return_value = ExternalSubscription(
        external_subscription_id="sub_test123",
        external_customer_id="cus_test123",
        status="active",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        canceled_at=None,
        external_price_id="price_test123",
    )
    mock.switch_subscription_price.return_value = ExternalSubscription(
        external_subscription_id="sub_test123",
        external_customer_id="cus_test123",
        status="active",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        canceled_at=None,
        external_price_id="price_test456",
    )
    mock.has_payment_method.return_value = False
    mock.get_charge_customer.return_value = None
    mock.update_customer.return_value = None
    mock.get_customer_portal_url.return_value = CustomerPortalResult(
        portal_url="https://billing.stripe.com/portal/test"
    )
    mock.create_subscription.return_value = ExternalSubscription(
        external_subscription_id="sub_trial123",
        external_customer_id="cus_test123",
        status="trialing",
        current_period_start=None,
        current_period_end=None,
        cancel_at_period_end=False,
        canceled_at=None,
        external_price_id="price_test123",
    )
    mock.construct_webhook_event.return_value = WebhookPayload(
        external_event_id="evt_test123",
        event_type="subscription.updated",
        raw={},
    )

    app.dependency_overrides[get_billing_provider] = lambda: mock
    yield mock
    app.dependency_overrides.pop(get_billing_provider, None)


@pytest.fixture
def no_roles_authenticated(client: TestClient) -> TestClient:
    rs = client.post(
        "/v1/auth/token",
        data={"username": "no_roles@example.org", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()

    client.headers = Headers({"Authorization": f"Bearer {rs['access_token']}"})

    return client


@pytest.fixture
async def admin_in_org2() -> None:
    """Add user 1 (admin@example.org) to Organization 2 directly in the DB."""
    async with TestSessionLocal() as session:
        session.add(UserOrganization(user_id=1, organization_id=2))
        await session.commit()


@pytest.fixture(name="client")
def _client() -> Generator[TestClient]:
    with TestClient(app) as c:
        yield c


@pytest.fixture
def admin_authenticated(client: TestClient) -> TestClient:
    rs = client.post(
        "/v1/auth/token",
        data={"username": "admin@example.org", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()

    client.headers = Headers({"Authorization": f"Bearer {rs['access_token']}"})

    return client


@pytest.fixture
def standard_authenticated(client: TestClient) -> TestClient:
    rs = client.post(
        "/v1/auth/token",
        data={"username": "standard@example.org", "password": "password"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    ).json()

    client.headers = Headers({"Authorization": f"Bearer {rs['access_token']}"})

    return client


@pytest.fixture
def organization2_admin_authenticated() -> Generator[TestClient]:
    with TestClient(app) as c:
        rs = c.post(
            "/v1/auth/token",
            data={"username": "admin2@example.org", "password": "password"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        ).json()

        c.headers = Headers({"Authorization": f"Bearer {rs['access_token']}"})

        yield c


@pytest.fixture
async def plan_with_price() -> dict:
    """Create a plan with one price directly in the DB. Returns {"plan": ..., "price": ...}."""  # noqa: E501
    async with TestSessionLocal() as session:
        plan = Plan(
            name="Pro",
            description="Pro plan",
            external_product_id="prod_test123",
            is_active=True,
        )
        session.add(plan)
        await session.flush()
        plan_id = plan.id

        price = PlanPrice(
            plan_id=plan_id,
            amount=999,
            currency="dkk",
            interval="month",
            interval_count=1,
            external_price_id="price_test123",
            is_active=True,
        )
        session.add(price)
        await session.flush()
        price_id = price.id

        await session.commit()

    return {
        "plan": {
            "id": plan_id,
            "name": "Pro",
            "description": "Pro plan",
            "external_product_id": "prod_test123",
            "is_active": True,
        },
        "price": {
            "id": price_id,
            "plan_id": plan_id,
            "amount": 999,
            "currency": "dkk",
            "interval": "month",
            "interval_count": 1,
            "external_price_id": "price_test123",
            "is_active": True,
        },
    }
