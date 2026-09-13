"""Direct unit tests for AuditLogService."""

from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.services.audit_log import AuditLogService
from tests.conftest import TestSessionLocal


def _admin_auth(user_id: int = 1, org_id: int = 1) -> Auth:
    return Auth(
        id=user_id,
        name="Alice Owner",
        email="admin@example.org",
        organization_id=org_id,
        roles=["Owner"],
        permissions=[p.value for p in PermEnum],
    )


# ---------------------------------------------------------------------------
# paginate
# ---------------------------------------------------------------------------


async def test_paginate_returns_paginated_response():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = AuditLogService(repos, _admin_auth())
            result = await service.paginate(page_size=10, page_number=1)

    assert result.total >= 0
    assert isinstance(result.items, list)


async def test_paginate_with_action_filter():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            service = AuditLogService(repos, _admin_auth())
            result = await service.paginate(
                page_size=10, page_number=1, action_filter="auth.login"
            )

    assert isinstance(result.items, list)
