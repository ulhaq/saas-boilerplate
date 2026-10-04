import builtins
from dataclasses import dataclass
from datetime import date
from enum import StrEnum
from typing import Annotated, Any

from fastapi import Depends, HTTPException, status

from src.foundation.core import composition
from src.foundation.core.config import settings
from src.foundation.core.exceptions import ValidationException
from src.foundation.core.module import NotificationCategory, NotificationRule
from src.foundation.core.realtime import RealtimeEvent, publish_to_user
from src.foundation.core.security import Auth
from src.foundation.enums import ErrorCode, NotificationEvent
from src.foundation.models.notification_preference import NotificationPreference
from src.foundation.models.user import User
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.schemas.common import PaginatedResponse
from src.foundation.schemas.notification import (
    NotificationOut,
    NotificationPreferenceIn,
    NotificationPreferenceOut,
    UnreadCountOut,
)
from src.foundation.services.access import authenticate
from src.foundation.services.email_content import format_date
from src.foundation.services.email_outbox import queue_email


def _category(key: StrEnum) -> NotificationCategory:
    category = composition.current().notification_categories.get(key)
    if category is None:
        raise ValueError(f"Unknown notification category {key!r}")
    return category


def _channels(
    category: NotificationCategory,
    preference: NotificationPreference | None,
) -> tuple[bool, bool]:
    """(in-app, email) for a user: their choice, else the category's
    defaults. A required email is sent whatever they chose."""
    in_app = preference.in_app if preference else category.in_app
    email = preference.email if preference else category.email
    return in_app, email or category.email_required


async def deliver_notification(  # noqa: PLR0913 - keyword-only
    repos: RepositoryManager,
    *,
    user: User,
    organization_id: int,
    category: StrEnum,
    notification_type: str,
    payload: dict[str, Any],
    email_template: str,
    email_data: dict[str, Any],
) -> None:
    """Notify ``user`` in-app and/or by email, as their preference for
    ``category`` says. Both are written in the caller's transaction: the
    email is queued (`queue_email`) and sent after commit. ``payload`` and
    ``email_data`` must be JSON-serializable."""
    in_app, email = _channels(
        _category(category),
        await repos.notification_preference.get(user.id, category),
    )
    if email:
        await queue_email(
            repos,
            address=user.email,
            user_name=user.name,
            email_template=email_template,
            locale=user.locale,
            data=email_data,
        )
    if in_app:
        notification = await repos.notification.create(
            user_id=user.id,
            organization_id=organization_id,
            notification_type=notification_type,
            payload=payload,
        )
        publish_to_user(
            repos.db,
            user.id,
            RealtimeEvent(
                type=NotificationEvent.CREATED,
                organization_id=organization_id,
                data={"id": notification.id, "notification_type": notification_type},
            ),
        )


@dataclass(frozen=True)
class RuleHandler:
    """The hook handler that carries out ``rule`` when its event is emitted.
    A `date` in the rule's data is stored as an ISO string on the in-app
    notification (the app formats it) and written in each recipient's locale
    in their email. Compares by its rule, so composing the same modules twice
    gives an equal `Composition`."""

    rule: NotificationRule

    async def __call__(self, **kwargs: Any) -> None:
        rule = self.rule
        required = {"repos", "organization_id", *rule.data}
        if rule.exclude_user is not None:
            required.add(rule.exclude_user)
        if missing := required - kwargs.keys():
            raise TypeError(
                f"Hook event {rule.event!r} lacks {sorted(missing)} "
                f"for notification {rule.notification_type!r}",
            )
        repos: RepositoryManager = kwargs["repos"]
        organization_id: int = kwargs["organization_id"]
        excluded = kwargs[rule.exclude_user] if rule.exclude_user else None
        data = {key: kwargs[key] for key in rule.data}
        payload = {
            key: value.isoformat() if isinstance(value, date) else value
            for key, value in data.items()
        }
        links = {
            key: f"{settings.frontend_url}{path}" for key, path in rule.links.items()
        }
        members = RepositoryManager(repos.db).user
        members.set_organization_scope(organization_id)
        for user in await members.list_with_permission(rule.recipients):
            if user.id == excluded:
                continue
            await deliver_notification(
                repos,
                user=user,
                organization_id=organization_id,
                category=rule.category,
                notification_type=rule.notification_type,
                payload=payload,
                email_template=rule.email_template,
                email_data={
                    **{
                        key: format_date(value, user.locale)
                        if isinstance(value, date)
                        else value
                        for key, value in data.items()
                    },
                    **links,
                },
            )


class NotificationService:
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.repos = repos
        self.current_user = current_user

    async def list(
        self,
        page_size: int,
        page_number: int,
    ) -> PaginatedResponse[NotificationOut]:
        items, total = await self.repos.notification.list_for_user(
            user_id=self.current_user.id,
            organization_id=self.current_user.organization_id,
            page_size=page_size,
            page_number=page_number,
        )
        return PaginatedResponse(
            items=[NotificationOut.model_validate(n) for n in items],
            page_size=page_size,
            page_number=page_number,
            total=total,
        )

    async def unread_count(self) -> UnreadCountOut:
        count = await self.repos.notification.count_unread(
            user_id=self.current_user.id,
            organization_id=self.current_user.organization_id,
        )
        return UnreadCountOut(count=count)

    async def mark_read(self, notification_id: int) -> NotificationOut:
        notification = await self.repos.notification.get(notification_id)
        if (
            notification is None
            or notification.user_id != self.current_user.id
            or notification.organization_id != self.current_user.organization_id
        ):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        notification = await self.repos.notification.mark_read(notification)
        self._publish_read()
        return NotificationOut.model_validate(notification)

    async def mark_all_read(self) -> None:
        await self.repos.notification.mark_all_read(
            user_id=self.current_user.id,
            organization_id=self.current_user.organization_id,
        )
        self._publish_read()

    def _publish_read(self) -> None:
        """Let the user's other tabs update their unread count."""
        publish_to_user(
            self.repos.db,
            self.current_user.id,
            RealtimeEvent(
                type=NotificationEvent.READ,
                organization_id=self.current_user.organization_id,
            ),
        )

    async def list_preferences(self) -> builtins.list[NotificationPreferenceOut]:
        """The categories offered to the user - those whose notifications they
        can get in the current organization - with their current choice."""
        saved = {
            p.category: p
            for p in await self.repos.notification_preference.list_for_user(
                self.current_user.id,
            )
        }
        preferences = []
        for category in composition.current().notification_categories.values():
            if (
                category.permission is not None
                and category.permission not in self.current_user.permissions
            ):
                continue
            in_app, email = _channels(category, saved.get(category.key))
            preferences.append(
                NotificationPreferenceOut(
                    category=category.key,
                    in_app=in_app,
                    email=email,
                    email_required=category.email_required,
                ),
            )
        return preferences

    async def update_preferences(
        self,
        schema_in: builtins.list[NotificationPreferenceIn],
    ) -> builtins.list[NotificationPreferenceOut]:
        """Save the user's choice for each listed category; others keep theirs."""
        categories = composition.current().notification_categories
        for item in schema_in:
            category = categories.get(item.category)
            if category is None:
                raise ValidationException(
                    f"Unknown notification category {item.category!r}",
                    error_code=ErrorCode.PARAMETER_INVALID,
                )
            if category.email_required and not item.email:
                raise ValidationException(
                    f"The {item.category!r} email can't be turned off",
                    error_code=ErrorCode.PARAMETER_INVALID,
                )
            await self.repos.notification_preference.upsert(
                user_id=self.current_user.id,
                category=item.category,
                in_app=item.in_app,
                email=item.email,
            )
        return await self.list_preferences()
