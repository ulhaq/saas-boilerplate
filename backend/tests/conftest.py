import hashlib
import os
from collections.abc import AsyncGenerator, Generator
from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from httpx import Headers
from sqlalchemy import NullPool, create_engine, make_url, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# The environment the settings read at import time, and the installed modules,
# are set up by the `tests.preload` plugin, which runs before this file.
import src.foundation.core.security as _security_mod
from src.bootstrap import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS
from src.foundation.core import realtime
from src.foundation.core.config import settings
from src.foundation.core.database import Base, get_db
from src.foundation.core.security import hash_secret
from src.foundation.models.organization import Organization
from src.foundation.models.permission import Permission
from src.foundation.models.role import Role
from src.foundation.models.user import User
from src.foundation.models.user_organization import UserOrganization
from src.init_db import INIT_AUTH_DATA
from src.main import app
from tests.preload import WITHOUT_MODULES

# Tests run against a real PostgreSQL server so Postgres-only behaviour (JSONB,
# partial indexes, advisory locks, constraint semantics) is exercised. They use
# the app's server and credentials (settings.db_connection), but never the app
# database itself: each pytest-xdist worker creates and drops its own
# `<db>_test_<worker>` database, so the role needs CREATEDB.
_app_url = make_url(settings.db_connection)
_worker = os.environ.get("PYTEST_XDIST_WORKER", "main")
TEST_DATABASE_URL = _app_url.set(database=f"{_app_url.database}_test_{_worker}")

# NullPool: TestClient runs the app on its own event loop, so connections must
# not be shared across loops.
test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
_sync_test_engine = create_engine(TEST_DATABASE_URL, poolclass=NullPool)
TestSessionLocal = async_sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=test_engine,
)


async def db() -> AsyncGenerator[AsyncSession]:
    async with TestSessionLocal() as session, session.begin():
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
def in_process_realtime_broker() -> Generator[None]:
    """Never reach a Redis named in .env: an unset REDIS_URL picks the
    in-process broker (`core/realtime.py`)."""
    original = settings.redis_url
    settings.redis_url = ""
    yield
    settings.redis_url = original


@pytest.fixture(autouse=True)
def realtime_broker() -> realtime.LocalBroker:
    """A fresh broker per test, so no subscription outlives its test."""
    broker = realtime.LocalBroker()
    realtime.install_broker(broker)
    return broker


@pytest.fixture(scope="session", autouse=True)
def fast_password_hashing() -> Generator[None]:
    original = _security_mod.crypt_context
    _security_mod.crypt_context = _FastCryptContext()  # ty: ignore[invalid-assignment]
    yield
    _security_mod.crypt_context = original


@pytest.fixture(scope="session", autouse=True)
def test_database() -> Generator[None]:
    """Create a fresh database (and schema) for this worker, drop it afterwards."""
    admin_engine = create_engine(
        TEST_DATABASE_URL.set(database="postgres"),
        poolclass=NullPool,
        isolation_level="AUTOCOMMIT",
    )
    name = TEST_DATABASE_URL.database
    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        conn.execute(text(f'CREATE DATABASE "{name}"'))

    Base.metadata.create_all(_sync_test_engine)
    yield

    with admin_engine.connect() as conn:
        conn.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
    admin_engine.dispose()


def _truncate_all_tables() -> None:
    # RESTART IDENTITY keeps seeded ids at 1, 2, ... which tests rely on
    tables = ", ".join(f'"{t.name}"' for t in Base.metadata.sorted_tables)
    with _sync_test_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE {tables} RESTART IDENTITY CASCADE"))


@pytest.fixture(autouse=True)
async def prepare_database() -> AsyncGenerator[None]:
    hashed_password = hash_secret("password")
    async with TestSessionLocal() as session:
        organizations = [
            Organization(name=organization["name"])
            for organization in INIT_AUTH_DATA["organizations"]
        ]
        session.add_all(organizations)

        permissions = [
            Permission(
                name=permission.value,
                description=PERMISSION_DESCRIPTIONS[permission],
            )
            for permission in ALL_PERMISSIONS
        ]
        session.add_all(permissions)

        roles = [
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
            for role in INIT_AUTH_DATA["roles"]
        ]
        session.add_all(roles)

        users = [
            User(
                name=user["name"],
                email=user["email"],
                password=hashed_password,
                roles=[
                    role for idx, role in enumerate(roles, 1) if idx in user["roles"]
                ],
            )
            for user in INIT_AUTH_DATA["users"]
        ]
        session.add_all(users)

        await session.flush()

        user_organizations = []
        for user_data, user in zip(INIT_AUTH_DATA["users"], users, strict=False):
            user_organizations.append(
                UserOrganization(
                    user_id=user.id,
                    organization_id=organizations[user_data["organization"] - 1].id,
                    last_active_at=datetime.now(UTC),
                ),
            )
        session.add_all(user_organizations)

        await session.commit()
    yield
    _truncate_all_tables()


@pytest.fixture(autouse=True)
def mock_send_email(mocker):
    """Prevent real SMTP calls in unit/integration tests."""
    mocker.patch("src.foundation.services.email_outbox.send_email")
    mocker.patch("src.foundation.services.auth.registration.send_email")
    mocker.patch("src.foundation.services.auth.invites.send_email")
    mocker.patch("src.foundation.services.auth.credentials.send_email")
    mocker.patch("src.foundation.services.user.send_email")
    mocker.patch("src.foundation.services.mailer._MAX_EMAIL_ATTEMPTS", 1)


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


def pytest_collection_modifyitems(items) -> None:
    for module in WITHOUT_MODULES:
        skip = pytest.mark.skip(reason=f"{module} is not installed")
        for item in items:
            if f"tests/{module}/" in item.nodeid or item.get_closest_marker(module):
                item.add_marker(skip)
