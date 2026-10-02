"""The manifest a product package hands to the platform.

A product (e.g. `src.example`) declares everything it contributes in one
`ProductModule`; the assembly layer (`src.products` -> `src.bootstrap`,
`src.main`, `worker.py`, `alembic/env.py`) iterates over the installed
modules. The platform defines this shape but never imports a product.
"""

from collections.abc import Callable, Coroutine, Mapping, Sequence
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from types import ModuleType
from typing import Any

from fastapi import APIRouter

from src.platform.core.hooks import Handler, HookEvent

# Receives the session factory (`ASYNC_SESSION_LOCAL`) and runs forever.
WorkerLoop = Callable[[Any], Coroutine[Any, Any, None]]


@dataclass(frozen=True, kw_only=True)
class ProductRouter:
    router: APIRouter
    tags: list[str]
    # Listed in the public OpenAPI schema for API-token consumers.
    public: bool = True


@dataclass(frozen=True, kw_only=True)
class ProductModule:
    name: str
    # Imported so the product's tables register on `Base.metadata` (Alembic).
    models: ModuleType
    permissions: Sequence[StrEnum] = ()
    permission_descriptions: Mapping[StrEnum, str] = field(default_factory=dict)
    # Extra grants and description overrides per platform default role name.
    default_role_permissions: Mapping[str, Sequence[StrEnum]] = field(
        default_factory=dict
    )
    default_role_descriptions: Mapping[str, str] = field(default_factory=dict)
    routers: Sequence[ProductRouter] = ()
    hooks: Mapping[HookEvent, Sequence[Handler]] = field(default_factory=dict)
    # Started by `worker.py`; wrap each iteration in `track_worker_run`.
    worker_loops: Sequence[WorkerLoop] = ()
    # Product emails: subjects keyed [locale][template] and a template root.
    email_subjects: Mapping[str, Mapping[str, str]] = field(default_factory=dict)
    template_directory: Path | None = None
