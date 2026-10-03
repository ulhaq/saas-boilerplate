"""The manifest a module hands to the foundation.

A module - the product (e.g. `src.example`) or an optional foundation module
(`src.billing`) - declares everything it contributes in one `Module`; the
assembly layer (`src.products` -> `src.bootstrap`, `src.main`, `worker.py`,
`alembic/env.py`) iterates over the installed modules. The foundation defines
this shape but never imports a module.
"""

from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

from src.foundation.core.entitlements import Entitlements
from src.foundation.core.hooks import Handler
from src.foundation.core.routing import RouterMount

# Async; keyword arguments `repos`, `user_id`, `email`; returns JSON-safe data.
UserDataExporter = Callable[..., Coroutine[Any, Any, dict[str, Any]]]

# Receives the session factory (`ASYNC_SESSION_LOCAL`) and runs forever.
WorkerLoop = Callable[[Any], Coroutine[Any, Any, None]]


@dataclass(frozen=True, kw_only=True)
class NotificationCategory:
    """A group of notifications a user can turn on or off per channel, on the
    notification settings page, labelled in the app under
    `notificationPreferences.categories.<key>`. Modules list their keys in a
    `StrEnum`, like their permissions."""

    key: StrEnum
    # What a user gets until they choose otherwise.
    in_app: bool = True
    email: bool = True
    # Account-critical email the user can't turn off (e.g. a failed payment).
    email_required: bool = False
    # Only offered to users holding it in their current organization - the
    # notifications go to them alone.
    permission: StrEnum | None = None


@dataclass(frozen=True, kw_only=True)
class NotificationRule:
    """Notify members when a hook event happens - the foundation's notification
    service subscribes to ``event`` for the module, so the emitting code knows
    nothing about notifications. The event's kwargs must include ``repos`` and
    ``organization_id``; each recipient gets it in-app and/or by email as their
    preference for ``category`` says."""

    event: StrEnum
    # A category the installed modules declare (`notification_categories`).
    category: StrEnum
    # Stored on the in-app notification; the app presents it by this type.
    notification_type: str
    email_template: str
    # Recipients: the organization's members holding this permission there.
    recipients: StrEnum
    # The event kwarg holding a user id not to notify (whoever caused it).
    exclude_user: str | None = None
    # Event kwargs copied into the notification payload and the email data;
    # JSON-safe, except a `date`, which each recipient sees in their locale.
    data: Sequence[str] = ()
    # Email-only links: data key -> path in the app (e.g. "/projects").
    links: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True, kw_only=True)
class Module:
    name: str
    # Imported so the product's tables register on `Base.metadata` (Alembic).
    models: ModuleType
    permissions: Sequence[StrEnum] = ()
    permission_descriptions: Mapping[StrEnum, str] = field(default_factory=dict)
    # Recorded in the audit log; listed in its action filter.
    audit_actions: Sequence[StrEnum] = ()
    # Extra grants and description overrides per foundation default role name.
    default_role_permissions: Mapping[str, Sequence[StrEnum]] = field(
        default_factory=dict,
    )
    default_role_descriptions: Mapping[str, str] = field(default_factory=dict)
    routers: Sequence[RouterMount] = ()
    # Hook events the module emits, beyond the foundation's `HookEvent`.
    hook_events: Sequence[StrEnum] = ()
    # Handlers for foundation `HookEvent`s and installed modules' events.
    hooks: Mapping[StrEnum, Sequence[Handler]] = field(default_factory=dict)
    # Started by `worker.py`; wrap each iteration in `track_worker_run`.
    worker_loops: Sequence[WorkerLoop] = ()
    # Product emails: subjects keyed [locale][template] and a template root.
    email_subjects: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    template_directory: Path | None = None
    # UTM tagging of the module's email links: template -> utm_medium (the
    # template is the campaign), and the template data keys holding links.
    email_campaigns: Mapping[str, str] = field(default_factory=dict)
    email_link_keys: Sequence[str] = ()
    # Notification groups users can opt out of, per channel (in-app, email).
    # Send them with `services.notification.deliver_notification`.
    notification_categories: Sequence[NotificationCategory] = ()
    # Notifications sent when a hook event happens, without code of the
    # module's own; for recipients a rule can't express, send them from a
    # handler with `deliver_notification`.
    notification_rules: Sequence[NotificationRule] = ()
    # Adds the module's personal data to a user's data export (GDPR): called
    # with `repos` (the request's RepositoryManager), `user_id` and `email`;
    # returns what it holds about that user, listed under the module's name.
    user_data_export: UserDataExporter | None = None
    # Answers the foundation's feature and limit checks; at most one installed
    # module provides it (`src.billing`, from its plans).
    entitlements: Entitlements | None = None
