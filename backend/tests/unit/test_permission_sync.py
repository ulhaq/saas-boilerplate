"""Tests for the deploy-time permission sync (services/permission.py)."""

from datetime import UTC, datetime

from sqlalchemy import select

from src.bootstrap import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS
from src.foundation.enums import OWNER_ROLE_NAME
from src.foundation.models.permission import Permission
from src.foundation.models.role import Role
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.services.permission import PermissionSync, sync_permissions
from tests.conftest import TestSessionLocal

DECLARED = {p.value: PERMISSION_DESCRIPTIONS[p] for p in ALL_PERMISSIONS}


async def _sync(declared: dict[str, str]) -> PermissionSync:
    async with TestSessionLocal() as session, session.begin():
        return await sync_permissions(RepositoryManager(session), declared)


async def _holders(permission: str) -> list[tuple[int, str]]:
    """(organization id, role name) of every role holding ``permission``."""
    async with TestSessionLocal() as session:
        roles = (await session.execute(select(Role))).unique().scalars().all()
        return sorted(
            (r.organization_id, r.name)
            for r in roles
            if any(p.name == permission for p in r.permissions)
        )


async def _permission(name: str) -> Permission | None:
    async with TestSessionLocal() as session:
        rs = await session.execute(select(Permission).where(Permission.name == name))
        return rs.scalar_one_or_none()


async def test_a_new_permission_is_added_and_granted_to_every_owner_only():
    result = await _sync({**DECLARED, "read:widget": "Allows reading widgets."})

    assert result.added == {"read:widget"}
    assert result.granted == 2  # one Owner role per seeded organization
    assert await _holders("read:widget") == [(1, OWNER_ROLE_NAME), (2, OWNER_ROLE_NAME)]


async def test_the_sync_is_idempotent():
    declared = {**DECLARED, "read:widget": "Allows reading widgets."}
    await _sync(declared)

    again = await _sync(declared)
    assert again.added == set()
    assert again.granted == 0


async def test_owners_get_permissions_they_were_never_granted():
    """An Owner role missing an existing permission (e.g. an organization
    created before a module was installed) gets it on the next sync."""
    async with TestSessionLocal() as session, session.begin():
        role = (
            (
                await session.execute(
                    select(Role).where(Role.organization_id == 2, Role.is_protected),
                )
            )
            .unique()
            .scalar_one()
        )
        role.permissions = [p for p in role.permissions if p.name != "read:audit_log"]

    assert await _holders("read:audit_log") == [(1, OWNER_ROLE_NAME)]
    assert (await _sync(DECLARED)).granted == 1
    assert (2, OWNER_ROLE_NAME) in await _holders("read:audit_log")


async def test_descriptions_are_refreshed_and_soft_deleted_permissions_restored():
    async with TestSessionLocal() as session, session.begin():
        permission = (
            await session.execute(
                select(Permission).where(Permission.name == "read:role"),
            )
        ).scalar_one()
        permission.description = "stale"
        permission.deleted_at = datetime.now(UTC)

    result = await _sync(DECLARED)

    assert result.added == set()
    restored = await _permission("read:role")
    assert restored
    assert restored.deleted_at is None
    assert restored.description == DECLARED["read:role"]


async def test_permissions_no_longer_declared_are_reported_not_removed():
    declared = {k: v for k, v in DECLARED.items() if k != "read:role"}

    result = await _sync(declared)

    assert result.undeclared == ["read:role"]
    assert await _permission("read:role") is not None
