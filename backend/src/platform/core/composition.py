"""Composed permission/role sets for the running product.

The platform defines its own enums in `src.platform.enums`; product domains
contribute theirs on top. The composition root (`src.bootstrap`) merges the
two and installs the result here at startup via `configure()`, so platform
code can consume the composed sets without importing the composition root
(which would create a platform -> product dependency).

Defaults to the bare platform sets, so the platform works standalone.
"""

from enum import StrEnum

from src.platform import enums as core_enums

ALL_PERMISSIONS: list[StrEnum] = [*core_enums.Permission]

PERMISSION_DESCRIPTIONS: dict[StrEnum, str] = {**core_enums.PERMISSION_DESCRIPTIONS}

DEFAULT_ROLES: list[tuple[str, str, list[StrEnum]]] = [*core_enums.DEFAULT_ROLES]


def configure(
    all_permissions: list[StrEnum],
    permission_descriptions: dict[StrEnum, str],
    default_roles: list[tuple[str, str, list[StrEnum]]],
) -> None:
    """Install the composed sets. Called once by the composition root."""
    ALL_PERMISSIONS[:] = all_permissions
    PERMISSION_DESCRIPTIONS.clear()
    PERMISSION_DESCRIPTIONS.update(permission_descriptions)
    DEFAULT_ROLES[:] = default_roles
