"""The manifest a module hands to the platform.

A module - the product (e.g. `src.example`) or an optional platform module
(`src.billing`) - declares everything it contributes in one `Module`; the
assembly layer (`src.products` -> `src.bootstrap`, `src.main`, `worker.py`,
`alembic/env.py`) iterates over the installed modules. The platform defines
this shape but never imports a module.
"""

from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

from src.platform.core.entitlements import Entitlements
from src.platform.core.hooks import Handler, HookEvent
from src.platform.core.routing import RouterMount

# Receives the session factory (`ASYNC_SESSION_LOCAL`) and runs forever.
WorkerLoop = Callable[[Any], Coroutine[Any, Any, None]]


@dataclass(frozen=True, kw_only=True)
class Module:
    name: str
    # Imported so the product's tables register on `Base.metadata` (Alembic).
    models: ModuleType
    permissions: Sequence[StrEnum] = ()
    permission_descriptions: Mapping[StrEnum, str] = field(default_factory=dict)
    # Recorded in the audit log; listed in its action filter.
    audit_actions: Sequence[StrEnum] = ()
    # Extra grants and description overrides per platform default role name.
    default_role_permissions: Mapping[str, Sequence[StrEnum]] = field(
        default_factory=dict
    )
    default_role_descriptions: Mapping[str, str] = field(default_factory=dict)
    routers: Sequence[RouterMount] = ()
    hooks: Mapping[HookEvent, Sequence[Handler]] = field(default_factory=dict)
    # Started by `worker.py`; wrap each iteration in `track_worker_run`.
    worker_loops: Sequence[WorkerLoop] = ()
    # Product emails: subjects keyed [locale][template] and a template root.
    email_subjects: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    template_directory: Path | None = None
    # UTM tagging of the module's email links: template -> utm_medium (the
    # template is the campaign), and the template data keys holding links.
    email_campaigns: Mapping[str, str] = field(default_factory=dict)
    email_link_keys: Sequence[str] = ()
    # Answers the platform's feature and limit checks; at most one installed
    # module provides it (`src.billing`, from its plans).
    entitlements: Entitlements | None = None
