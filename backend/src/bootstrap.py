"""Composition root - wires the installed product modules into the generic
SaaS core.

The products are listed in `src.products`; each declares what it contributes
in a `ProductModule` manifest. The core never imports domain code: it emits
hooks and consumes the composed permission/role sets defined here.
"""

from collections.abc import Sequence
from enum import StrEnum

from src.platform import enums as core_enums
from src.platform.core import composition
from src.platform.core.composition import Composition, RoleSpec
from src.platform.core.entitlements import UNLIMITED
from src.platform.core.hooks import Handler, HookEvent
from src.platform.core.product import ProductModule
from src.products import MODULES

ALL_PERMISSIONS: list[StrEnum] = [
    *core_enums.Permission,
    *(permission for product in MODULES for permission in product.permissions),
]

PERMISSION_DESCRIPTIONS: dict[StrEnum, str] = {
    **core_enums.PERMISSION_DESCRIPTIONS,
    **{
        permission: description
        for product in MODULES
        for permission, description in product.permission_descriptions.items()
    },
}


# Every action the installed modules record, as one enum named like the
# platform's: the audit log filters by it (`audit_log.build_router`).
AUDIT_ACTION: type[StrEnum] = StrEnum(
    "AuditAction",
    [
        (action.name, action.value)
        for action in [
            *core_enums.AuditAction,
            *(action for product in MODULES for action in product.audit_actions),
        ]
    ],
)


def compose_default_roles(
    roles: Sequence[RoleSpec], products: Sequence[ProductModule]
) -> list[RoleSpec]:
    """Add each product's grants to the platform default roles, and apply its
    description overrides (a later product wins)."""
    composed = []
    for name, description, permissions in roles:
        grants = [*permissions]
        for product in products:
            description = product.default_role_descriptions.get(name, description)
            grants.extend(product.default_role_permissions.get(name, []))
        composed.append((name, description, grants))
    return composed


def compose(products: Sequence[ProductModule]) -> Composition:
    """Merge what ``products`` add to the platform (in list order) into one
    read-only `Composition`."""
    providers = [p.entitlements for p in products if p.entitlements is not None]
    if len(providers) > 1:
        raise ValueError("More than one installed module provides entitlements")
    hook_handlers: dict[HookEvent, list[Handler]] = {}
    email_subjects: dict[str, dict[str, str]] = {}
    for product in products:
        for event, handlers in product.hooks.items():
            hook_handlers.setdefault(event, []).extend(handlers)
        for locale, subjects in product.email_subjects.items():
            email_subjects.setdefault(locale, {}).update(subjects)
    return Composition(
        default_roles=compose_default_roles(core_enums.DEFAULT_ROLES, products),
        hooks={event: tuple(handlers) for event, handlers in hook_handlers.items()},
        email_subjects=email_subjects,
        template_directories=[
            product.template_directory
            for product in products
            if product.template_directory
        ],
        entitlements=providers[0] if providers else UNLIMITED,
        email_campaigns={
            template: medium
            for product in products
            for template, medium in product.email_campaigns.items()
        },
        email_link_keys=frozenset(
            key for product in products for key in product.email_link_keys
        ),
    )


def bootstrap() -> None:
    """Install the installed products' composition. Idempotent; called at
    process startup by both the API (`src.main`) and the worker (`worker.py`)."""
    composition.install(compose(MODULES))
