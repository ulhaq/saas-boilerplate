"""Composition root - wires the installed product modules into the generic
SaaS core.

The products are listed in `src.products`; each declares what it contributes
in a `ProductModule` manifest. The core never imports domain code: it emits
hooks and consumes the composed permission/role sets defined here.
"""

from collections.abc import Sequence
from enum import StrEnum

from src.platform import enums as core_enums
from src.platform.core import composition, hooks
from src.platform.core.product import ProductModule
from src.platform.core.template import add_template_directory
from src.platform.services.email_content import register_email_subjects
from src.products import PRODUCTS

ALL_PERMISSIONS: list[StrEnum] = [
    *core_enums.Permission,
    *(permission for product in PRODUCTS for permission in product.permissions),
]

PERMISSION_DESCRIPTIONS: dict[StrEnum, str] = {
    **core_enums.PERMISSION_DESCRIPTIONS,
    **{
        permission: description
        for product in PRODUCTS
        for permission, description in product.permission_descriptions.items()
    },
}


type RoleSpec = tuple[str, str, list[StrEnum]]


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


DEFAULT_ROLES: list[RoleSpec] = compose_default_roles(
    core_enums.DEFAULT_ROLES, PRODUCTS
)

_bootstrapped = False


def bootstrap() -> None:
    """Install the composed sets and register each product's hooks and
    emails. Idempotent; called at process startup by both the API
    (`src.main`) and the worker (`worker.py`)."""
    global _bootstrapped
    if _bootstrapped:
        return
    composition.configure(ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS, DEFAULT_ROLES)
    for product in PRODUCTS:
        for event, handlers in product.hooks.items():
            for handler in handlers:
                hooks.register(event, handler)
        if product.email_subjects:
            register_email_subjects(
                {locale: dict(s) for locale, s in product.email_subjects.items()}
            )
        if product.template_directory:
            add_template_directory(product.template_directory)
    _bootstrapped = True
