"""Composition root - wires the product domain module into the generic SaaS core.

This is the only place (besides the product package itself) that may import
from `src.example`. The core never imports domain code; it emits hooks and
consumes the composed permission/role sets defined here.

For a new product built on this boilerplate:
1. Replace the `src.example` imports below with your own domain module (or
   remove them entirely to start from the bare platform).
2. Adjust ALL_PERMISSIONS / PERMISSION_DESCRIPTIONS / DEFAULT_ROLES composition.
3. Register your domain's hook handlers, email subjects, and template
   directories in `bootstrap()`.
"""

from enum import StrEnum

from src.example.enums import (
    EXAMPLE_DEFAULT_ROLE_DESCRIPTIONS,
    EXAMPLE_DEFAULT_ROLE_PERMISSIONS,
    EXAMPLE_PERMISSION_DESCRIPTIONS,
    ExamplePermission,
)
from src.example.hooks import register_example_hooks
from src.platform import enums as core_enums
from src.platform.core import composition

ALL_PERMISSIONS: list[StrEnum] = [*core_enums.Permission, *ExamplePermission]

PERMISSION_DESCRIPTIONS: dict[StrEnum, str] = {
    **core_enums.PERMISSION_DESCRIPTIONS,
    **EXAMPLE_PERMISSION_DESCRIPTIONS,
}

DEFAULT_ROLES: list[tuple[str, str, list[StrEnum]]] = [
    (
        name,
        EXAMPLE_DEFAULT_ROLE_DESCRIPTIONS.get(name, description),
        [*permissions, *EXAMPLE_DEFAULT_ROLE_PERMISSIONS.get(name, [])],
    )
    for name, description, permissions in core_enums.DEFAULT_ROLES
]

_bootstrapped = False


def bootstrap() -> None:
    """Register domain hook handlers. Idempotent; called at process startup
    by both the API (`src.main`) and the worker (`worker.py`)."""
    global _bootstrapped
    if _bootstrapped:
        return
    composition.configure(ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS, DEFAULT_ROLES)
    register_example_hooks()
    # A product that sends its own email also registers subjects and templates:
    #   register_email_subjects(EXAMPLE_EMAIL_SUBJECTS)
    #   add_template_directory(
    #       Path(__file__).resolve().parent / "example" / "templates"
    #   )
    _bootstrapped = True
