"""What the installed products add to the foundation, as one read-only object.

The foundation defines its own enums, hooks, email subjects and templates; product
domains contribute theirs on top. The composition root (`src.bootstrap`) merges
them into a `Composition` and installs it here at startup via `install()`, so
foundation code can consume the result without importing the composition root
(which would create a foundation -> product dependency).

Reading it before `install()` raises instead of silently falling back to the
bare foundation - a process that forgot `bootstrap()` would otherwise seed new
organizations without the product's permissions and skip its hook handlers.
A foundation without products still calls `bootstrap()`, with no products listed.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.foundation.core.entitlements import Entitlements
    from src.foundation.core.hooks import Handler, HookEvent
    from src.foundation.core.module import NotificationCategory, UserDataExporter

type RoleSpec = tuple[str, str, Sequence[StrEnum]]


@dataclass(frozen=True, kw_only=True)
class Composition:
    # Seeded into every new organization: (name, description, permissions).
    default_roles: Sequence[RoleSpec]
    # Run in order by `hooks.emit`.
    hooks: Mapping[HookEvent, Sequence[Handler]]
    # Product email subject lines, keyed [locale][template].
    email_subjects: Mapping[str, Mapping[str, str]]
    # Product template roots, searched after the foundation's own.
    template_directories: Sequence[Path]
    # UTM tagging of module emails: template -> medium, and link data keys.
    email_campaigns: Mapping[str, str]
    email_link_keys: frozenset[str]
    # Each module's share of a user's data export, by module name.
    user_data_exporters: Mapping[str, UserDataExporter]
    # Notification groups users can opt out of, by key value (requests send
    # it as a string), in module order.
    notification_categories: Mapping[str, NotificationCategory]
    # Features and limits per organization (`UNLIMITED` without a plan module).
    entitlements: Entitlements


_installed: Composition | None = None


def install(composition: Composition) -> None:
    """Install the composition. Called once per process by the composition
    root; installing a different one later is an error."""
    global _installed  # noqa: PLW0603 - process-wide singleton
    if _installed is None:
        _installed = composition
    elif _installed != composition:
        raise RuntimeError("A different composition is already installed")


def current() -> Composition:
    if _installed is None:
        raise RuntimeError(
            "No composition installed - call src.bootstrap.bootstrap() at startup",
        )
    return _installed
