from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, ClassVar

from sqlalchemy import Select, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.enums import OWNER_ROLE_NAME
from src.platform.models.password_reset_token import PasswordResetToken
from src.platform.models.permission import Permission
from src.platform.models.role import Role
from src.platform.models.user import User
from src.platform.models.user_organization import UserOrganization
from src.platform.repositories.abc import SoftDeleteRepositoryABC
from src.platform.repositories.base import (
    OrganizationScopedRepository,
    SQLResourceRepository,
)


class UserRepositoryABC(SoftDeleteRepositoryABC[User], ABC):
    @abstractmethod
    async def get_by_email(
        self, email: str, include_deleted: bool = False
    ) -> User | None: ...

    @abstractmethod
    async def add_roles(self, user: User, *role_ids: int) -> None: ...

    @abstractmethod
    async def remove_roles(self, user: User, *role_ids: int) -> None: ...

    @abstractmethod
    async def get_password_reset_token(
        self, user: User
    ) -> PasswordResetToken | None: ...

    @abstractmethod
    async def create_password_reset_token(
        self, *, user: User, token: str
    ) -> PasswordResetToken: ...

    @abstractmethod
    async def delete_password_reset_token(self, *, user: User) -> None: ...

    @abstractmethod
    async def has_other_user_with_permission(
        self, permission: str, exclude_user_id: int
    ) -> bool: ...

    @abstractmethod
    async def has_other_user_with_role(
        self, role_id: int, exclude_user_id: int
    ) -> bool: ...

    @abstractmethod
    async def get_owner_for_organization(self, organization_id: int) -> User | None: ...

    @abstractmethod
    async def count_for_org(self, organization_id: int) -> int: ...


class UserRepository(OrganizationScopedRepository[User], UserRepositoryABC):
    search_fields: ClassVar[list[str]] = ["name", "email"]

    def __init__(self, db: AsyncSession) -> None:
        super().__init__(User, db)

    def _scope_filter(self, stmt: Select, organization_id: int) -> Select:
        # User has no organization_id column - scope via membership join.
        return stmt.join(UserOrganization, UserOrganization.user_id == User.id).filter(
            UserOrganization.organization_id == organization_id
        )

    async def create(self, **kwargs: Any) -> User:
        # Skip OrganizationScopedRepository.create - User has no organization_id column.
        return await SQLResourceRepository.create(self, **kwargs)

    async def get_by_email(
        self, email: str, include_deleted: bool = False
    ) -> User | None:
        stmt = select(User).where(User.email == email)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def add_roles(self, user: User, *role_ids: int) -> None:
        await self.add_relationship(user, Role, "roles", *role_ids)

    async def remove_roles(self, user: User, *role_ids: int) -> None:
        await self.remove_relationship(user, "roles", *role_ids)

    async def get_password_reset_token(self, user: User) -> PasswordResetToken | None:
        stmt = select(PasswordResetToken).filter(PasswordResetToken.user_id == user.id)

        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def create_password_reset_token(
        self, *, user: User, token: str
    ) -> PasswordResetToken:
        instance = PasswordResetToken(
            user_id=user.id, token=token, created_at=datetime.now(UTC)
        )

        self.db.add(instance)

        return await self.save(instance)

    async def delete_password_reset_token(self, *, user: User) -> None:
        stmt = delete(PasswordResetToken).filter(PasswordResetToken.user_id == user.id)

        await self.db.execute(stmt)

        await self.save()

    async def has_other_user_with_permission(
        self, permission: str, exclude_user_id: int
    ) -> bool:
        stmt = (
            select(User)
            .join(User.roles)
            .join(Role.permissions)
            .where(User.id != exclude_user_id, Permission.name == permission)
        )
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none() is not None

    async def has_other_user_with_role(
        self, role_id: int, exclude_user_id: int
    ) -> bool:
        stmt = (
            select(User)
            .join(User.roles)
            .where(Role.id == role_id, User.id != exclude_user_id)
        )
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none() is not None

    async def count_for_org(self, organization_id: int) -> int:
        stmt = (
            select(func.count())
            .select_from(UserOrganization)
            .where(UserOrganization.organization_id == organization_id)
        )
        rs = await self.db.execute(stmt)
        return int(rs.scalar_one())

    async def get_owner_for_organization(self, organization_id: int) -> User | None:
        stmt = (
            select(User)
            .join(User.roles)
            .join(UserOrganization, UserOrganization.user_id == User.id)
            .where(
                UserOrganization.organization_id == organization_id,
                Role.organization_id == organization_id,
                Role.is_protected.is_(True),
                Role.name == OWNER_ROLE_NAME,
            )
        )
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()
