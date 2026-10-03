from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from functools import cached_property

from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.core.database import DbSession
from src.platform.repositories.api_token import ApiTokenRepository
from src.platform.repositories.audit_log import AuditLogRepository
from src.platform.repositories.email_outbox import EmailOutboxRepository
from src.platform.repositories.email_verification_token import (
    EmailVerificationTokenRepository,
)
from src.platform.repositories.invitation import InvitationRepository
from src.platform.repositories.login_throttle import LoginThrottleRepository
from src.platform.repositories.notification import NotificationRepository
from src.platform.repositories.organization import OrganizationRepository
from src.platform.repositories.permission import PermissionRepository
from src.platform.repositories.refresh_token import RefreshTokenRepository
from src.platform.repositories.role import RoleRepository
from src.platform.repositories.user import UserRepository
from src.platform.repositories.user_organization import UserOrganizationRepository
from src.platform.repositories.worker_run import WorkerRunRepository


class RepositoryManager:
    db: AsyncSession

    def __init__(self, db: DbSession) -> None:
        self.db = db

    @cached_property
    def audit_log(self) -> AuditLogRepository:
        return AuditLogRepository(self.db)

    @cached_property
    def api_token(self) -> ApiTokenRepository:
        return ApiTokenRepository(self.db)

    @cached_property
    def organization(self) -> OrganizationRepository:
        return OrganizationRepository(self.db)

    @cached_property
    def user(self) -> UserRepository:
        return UserRepository(self.db)

    @cached_property
    def role(self) -> RoleRepository:
        return RoleRepository(self.db)

    @cached_property
    def permission(self) -> PermissionRepository:
        return PermissionRepository(self.db)

    @cached_property
    def refresh_token(self) -> RefreshTokenRepository:
        return RefreshTokenRepository(self.db)

    @cached_property
    def user_organization(self) -> UserOrganizationRepository:
        return UserOrganizationRepository(self.db)

    @cached_property
    def email_verification_token(self) -> EmailVerificationTokenRepository:
        return EmailVerificationTokenRepository(self.db)

    @cached_property
    def invitation(self) -> InvitationRepository:
        return InvitationRepository(self.db)

    @cached_property
    def notification(self) -> NotificationRepository:
        return NotificationRepository(self.db)

    @cached_property
    def worker_run(self) -> WorkerRunRepository:
        return WorkerRunRepository(self.db)

    async def commit_before_raise(self) -> None:
        """Commit the request transaction now, ahead of an exception that
        would otherwise roll it back.

        Only for writes that must survive the failure they report - a
        failed-attempt counter, a session revocation. Everything else commits
        with the request (see `DbSession`). Raise right after: the session
        must not be used again.
        """
        await self.db.commit()

    @cached_property
    def email_outbox(self) -> EmailOutboxRepository:
        return EmailOutboxRepository(self.db)

    @cached_property
    def login_throttle(self) -> LoginThrottleRepository:
        return LoginThrottleRepository(self.db)

    @asynccontextmanager
    async def savepoint(self) -> AsyncGenerator[None]:
        async with self.db.begin_nested():
            yield
