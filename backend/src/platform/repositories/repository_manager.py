from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.core.database import get_db
from src.platform.repositories.api_token import ApiTokenRepository
from src.platform.repositories.audit_log import AuditLogRepository
from src.platform.repositories.billing import (
    PlanFeatureRepository,
    PlanPriceRepository,
    PlanRepository,
    PlanSettingRepository,
    PlanUsageRepository,
    SubscriptionRepository,
    WebhookEventRepository,
)
from src.platform.repositories.email_verification_token import (
    EmailVerificationTokenRepository,
)
from src.platform.repositories.invite_token import InviteTokenRepository
from src.platform.repositories.notification import NotificationRepository
from src.platform.repositories.organization import OrganizationRepository
from src.platform.repositories.permission import PermissionRepository
from src.platform.repositories.refresh_token import RefreshTokenRepository
from src.platform.repositories.role import RoleRepository
from src.platform.repositories.user import UserRepository
from src.platform.repositories.user_organization import UserOrganizationRepository
from src.platform.repositories.waitlist_entry import WaitlistEntryRepository
from src.platform.repositories.worker_run import WorkerRunRepository


class RepositoryManager:
    db: AsyncSession

    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        self.db = db
        self._audit_log: AuditLogRepository | None = None
        self._api_token: ApiTokenRepository | None = None
        self._notification: NotificationRepository | None = None
        self._worker_run: WorkerRunRepository | None = None
        self._organization: OrganizationRepository | None = None
        self._user: UserRepository | None = None
        self._role: RoleRepository | None = None
        self._permission: PermissionRepository | None = None
        self._refresh_token: RefreshTokenRepository | None = None
        self._user_organization: UserOrganizationRepository | None = None
        self._plan: PlanRepository | None = None
        self._plan_price: PlanPriceRepository | None = None
        self._plan_feature: PlanFeatureRepository | None = None
        self._plan_setting: PlanSettingRepository | None = None
        self._plan_usage: PlanUsageRepository | None = None
        self._subscription: SubscriptionRepository | None = None
        self._webhook_event: WebhookEventRepository | None = None
        self._email_verification_token: EmailVerificationTokenRepository | None = None
        self._invite_token: InviteTokenRepository | None = None
        self._waitlist_entry: WaitlistEntryRepository | None = None

    @property
    def audit_log(self) -> AuditLogRepository:
        if self._audit_log is None:
            self._audit_log = AuditLogRepository(self.db)
        return self._audit_log

    @property
    def api_token(self) -> ApiTokenRepository:
        if self._api_token is None:
            self._api_token = ApiTokenRepository(self.db)
        return self._api_token

    @property
    def organization(self) -> OrganizationRepository:
        if self._organization is None:
            self._organization = OrganizationRepository(self.db)
        return self._organization

    @property
    def user(self) -> UserRepository:
        if self._user is None:
            self._user = UserRepository(self.db)
        return self._user

    @property
    def role(self) -> RoleRepository:
        if self._role is None:
            self._role = RoleRepository(self.db)
        return self._role

    @property
    def permission(self) -> PermissionRepository:
        if self._permission is None:
            self._permission = PermissionRepository(self.db)
        return self._permission

    @property
    def refresh_token(self) -> RefreshTokenRepository:
        if self._refresh_token is None:
            self._refresh_token = RefreshTokenRepository(self.db)
        return self._refresh_token

    @property
    def user_organization(self) -> UserOrganizationRepository:
        if self._user_organization is None:
            self._user_organization = UserOrganizationRepository(self.db)
        return self._user_organization

    @property
    def plan(self) -> PlanRepository:
        if self._plan is None:
            self._plan = PlanRepository(self.db)
        return self._plan

    @property
    def plan_price(self) -> PlanPriceRepository:
        if self._plan_price is None:
            self._plan_price = PlanPriceRepository(self.db)
        return self._plan_price

    @property
    def plan_feature(self) -> PlanFeatureRepository:
        if self._plan_feature is None:
            self._plan_feature = PlanFeatureRepository(self.db)
        return self._plan_feature

    @property
    def plan_setting(self) -> PlanSettingRepository:
        if self._plan_setting is None:
            self._plan_setting = PlanSettingRepository(self.db)
        return self._plan_setting

    @property
    def plan_usage(self) -> PlanUsageRepository:
        if self._plan_usage is None:
            self._plan_usage = PlanUsageRepository(self.db)
        return self._plan_usage

    @property
    def subscription(self) -> SubscriptionRepository:
        if self._subscription is None:
            self._subscription = SubscriptionRepository(self.db)
        return self._subscription

    @property
    def webhook_event(self) -> WebhookEventRepository:
        if self._webhook_event is None:
            self._webhook_event = WebhookEventRepository(self.db)
        return self._webhook_event

    @property
    def email_verification_token(self) -> EmailVerificationTokenRepository:
        if self._email_verification_token is None:
            self._email_verification_token = EmailVerificationTokenRepository(self.db)
        return self._email_verification_token

    @property
    def invite_token(self) -> InviteTokenRepository:
        if self._invite_token is None:
            self._invite_token = InviteTokenRepository(self.db)
        return self._invite_token

    @property
    def notification(self) -> NotificationRepository:
        if self._notification is None:
            self._notification = NotificationRepository(self.db)
        return self._notification

    @property
    def worker_run(self) -> WorkerRunRepository:
        if self._worker_run is None:
            self._worker_run = WorkerRunRepository(self.db)
        return self._worker_run

    @property
    def waitlist_entry(self) -> WaitlistEntryRepository:
        if self._waitlist_entry is None:
            self._waitlist_entry = WaitlistEntryRepository(self.db)
        return self._waitlist_entry

    @asynccontextmanager
    async def savepoint(self) -> AsyncGenerator[None]:
        async with self.db.begin_nested():
            yield
