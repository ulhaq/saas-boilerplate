"""Direct unit tests for RoleService and PermissionService."""

import pytest

from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    PermissionDeniedException,
)
from src.platform.core.security import Auth
from src.platform.enums import Permission as PermEnum
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.common import PageQueryParams
from src.platform.schemas.permission import PermissionIn, PermissionOut, PermissionPatch
from src.platform.schemas.role import RoleIn, RoleOut, RolePatch, RolePermissionIn
from src.platform.services.permission import PermissionService
from src.platform.services.role import RoleService
from tests.conftest import TestSessionLocal


def _admin_auth(org_id: int = 1) -> Auth:
    return Auth(
        id=1,
        name="Alice Owner",
        email="admin@example.org",
        organization_id=org_id,
        roles=["Owner"],
        permissions=[p.value for p in PermEnum],
    )


def _make_role_service(session, auth: Auth) -> RoleService:
    repos = RepositoryManager(session)
    return RoleService(repos, auth)


def _make_perm_service(session) -> PermissionService:
    repos = RepositoryManager(session)
    return PermissionService(repos)


# ---------------------------------------------------------------------------
# RoleService - paginate
# ---------------------------------------------------------------------------


async def test_paginate_roles():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            result = await service.paginate(
                RoleOut,
                PageQueryParams(page_number=1, page_size=10, sort=[], filters=[]),
            )
    assert result.total >= 1


# ---------------------------------------------------------------------------
# RoleService - create_role
# ---------------------------------------------------------------------------


async def test_create_role_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            out = await service.create_role(
                RoleIn(name="Editor", description="Can edit")
            )
    assert out.name == "Editor"


async def test_create_role_duplicate_name_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            await service.create_role(RoleIn(name="DupeRole"))

    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            with pytest.raises(AlreadyExistsException):
                await service.create_role(RoleIn(name="DupeRole"))


# ---------------------------------------------------------------------------
# RoleService - get_role
# ---------------------------------------------------------------------------


async def test_get_role_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            role = await service.create_role(RoleIn(name="Fetcher"))
            out = await service.get_role(role.id)
    assert out.name == "Fetcher"


async def test_get_role_not_found_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            with pytest.raises(NotFoundException):
                await service.get_role(9999)


# ---------------------------------------------------------------------------
# RoleService - patch_role
# ---------------------------------------------------------------------------


async def test_patch_role_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            role = await service.create_role(RoleIn(name="PatchMe"))
            out = await service.patch_role(role.id, RolePatch(name="Patched"))
    assert out.name == "Patched"


async def test_patch_protected_role_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            # Find the Owner (protected) role for org 1
            roles = await repos.role.unscoped.get_all()
            owner_role = next(
                r for r in roles if r.is_protected and r.organization_id == 1
            )
            service = _make_role_service(session, _admin_auth())
            with pytest.raises(PermissionDeniedException):
                await service.patch_role(owner_role.id, RolePatch(name="Hacked"))


async def test_patch_role_duplicate_name_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            await service.create_role(RoleIn(name="RoleA"))
            r2 = await service.create_role(RoleIn(name="RoleB"))
            with pytest.raises(AlreadyExistsException):
                await service.patch_role(r2.id, RolePatch(name="RoleA"))


# ---------------------------------------------------------------------------
# RoleService - delete_role
# ---------------------------------------------------------------------------


async def test_delete_role_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_role_service(session, _admin_auth())
            role = await service.create_role(RoleIn(name="ToDelete"))
            await service.delete_role(role.id)


async def test_delete_protected_role_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            roles = await repos.role.unscoped.get_all()
            owner_role = next(
                r for r in roles if r.is_protected and r.organization_id == 1
            )
            service = _make_role_service(session, _admin_auth())
            with pytest.raises(PermissionDeniedException):
                await service.delete_role(owner_role.id)


# ---------------------------------------------------------------------------
# RoleService - manage_permissions
# ---------------------------------------------------------------------------


async def test_manage_permissions_adds_and_removes():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            permissions = await repos.permission.get_all()
            perm_ids = [p.id for p in permissions[:3]]

            service = _make_role_service(session, _admin_auth())
            role = await service.create_role(RoleIn(name="PermRole"))

            # Add 3 permissions
            out = await service.manage_permissions(
                role.id, RolePermissionIn(permission_ids=perm_ids)
            )
            assert len(out.permissions) == 3

            # Remove all permissions
            out2 = await service.manage_permissions(
                role.id, RolePermissionIn(permission_ids=[])
            )
            assert len(out2.permissions) == 0


async def test_manage_permissions_protected_role_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            repos = RepositoryManager(session)
            roles = await repos.role.unscoped.get_all()
            owner_role = next(
                r for r in roles if r.is_protected and r.organization_id == 1
            )
            service = _make_role_service(session, _admin_auth())
            with pytest.raises(PermissionDeniedException):
                await service.manage_permissions(
                    owner_role.id, RolePermissionIn(permission_ids=[])
                )


# ---------------------------------------------------------------------------
# PermissionService - paginate
# ---------------------------------------------------------------------------


async def test_paginate_permissions():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            result = await service.paginate(
                PermissionOut,
                PageQueryParams(page_number=1, page_size=10, sort=[], filters=[]),
            )
    assert result.total >= 1


# ---------------------------------------------------------------------------
# PermissionService - create_permission
# ---------------------------------------------------------------------------


async def test_create_permission_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            out = await service.create_permission(
                PermissionIn(name="custom:do_thing", description="A custom permission")
            )
    assert out.name == "custom:do_thing"


async def test_create_permission_duplicate_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            # All seeded permissions already exist in the DB
            permissions = await service.get_all()
            perm_name = permissions[0].name
            with pytest.raises(AlreadyExistsException):
                await service.create_permission(PermissionIn(name=perm_name))


# ---------------------------------------------------------------------------
# PermissionService - update_permission
# ---------------------------------------------------------------------------


async def test_update_permission_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            created = await service.create_permission(
                PermissionIn(name="perm:to_update")
            )
            out = await service.update_permission(
                created.id, PermissionIn(name="perm:updated", description="Updated")
            )
    assert out.name == "perm:updated"


async def test_update_permission_duplicate_name_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            permissions = await service.get_all()
            perm1, perm2 = permissions[0], permissions[1]
            with pytest.raises(AlreadyExistsException):
                await service.update_permission(perm2.id, PermissionIn(name=perm1.name))


# ---------------------------------------------------------------------------
# PermissionService - patch_permission
# ---------------------------------------------------------------------------


async def test_patch_permission_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            created = await service.create_permission(
                PermissionIn(name="perm:to_patch")
            )
            out = await service.patch_permission(
                created.id, PermissionPatch(description="Patched desc")
            )
    assert out.description == "Patched desc"


async def test_patch_permission_duplicate_name_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            permissions = await service.get_all()
            perm1, perm2 = permissions[0], permissions[1]
            with pytest.raises(AlreadyExistsException):
                await service.patch_permission(
                    perm2.id, PermissionPatch(name=perm1.name)
                )


# ---------------------------------------------------------------------------
# PermissionService - get_permission / delete_permission
# ---------------------------------------------------------------------------


async def test_get_permission_found():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            permissions = await service.get_all()
            first_id = permissions[0].id
            out = await service.get_permission(first_id)
    assert out.id == first_id


async def test_get_permission_not_found_raises():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            with pytest.raises(NotFoundException):
                await service.get_permission(9999)


async def test_delete_permission_success():
    async with TestSessionLocal() as session:
        async with session.begin():
            service = _make_perm_service(session)
            created = await service.create_permission(
                PermissionIn(name="perm:to_delete")
            )
            await service.delete_permission(created.id)
