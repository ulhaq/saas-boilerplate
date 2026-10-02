"""Tests for composing product manifests in src/bootstrap.py."""

from enum import StrEnum
from types import ModuleType

from src.bootstrap import RoleSpec, compose_default_roles
from src.platform.core.product import ProductModule


class _Perm(StrEnum):
    READ_WIDGET = "read:widget"
    EDIT_WIDGET = "edit:widget"
    READ_GADGET = "read:gadget"


def _product(name: str, **kwargs) -> ProductModule:
    return ProductModule(name=name, models=ModuleType(name), **kwargs)


def test_compose_default_roles_adds_each_products_grants():
    roles: list[RoleSpec] = [("Member", "Default member", [_Perm.READ_WIDGET])]
    widgets = _product(
        "widgets", default_role_permissions={"Member": [_Perm.EDIT_WIDGET]}
    )
    gadgets = _product(
        "gadgets", default_role_permissions={"Member": [_Perm.READ_GADGET]}
    )

    assert compose_default_roles(roles, [widgets, gadgets]) == [
        (
            "Member",
            "Default member",
            [_Perm.READ_WIDGET, _Perm.EDIT_WIDGET, _Perm.READ_GADGET],
        )
    ]


def test_compose_default_roles_applies_description_overrides_last_wins():
    roles: list[RoleSpec] = [
        ("Member", "Default member", []),
        ("Admin", "Default admin", []),
    ]
    first = _product("first", default_role_descriptions={"Member": "First's text"})
    second = _product("second", default_role_descriptions={"Member": "Second's text"})

    composed = compose_default_roles(roles, [first, second])

    assert composed == [("Member", "Second's text", []), ("Admin", "Default admin", [])]


def test_compose_default_roles_does_not_mutate_platform_roles():
    platform_grants: list[StrEnum] = [_Perm.READ_WIDGET]
    roles: list[RoleSpec] = [("Member", "Default member", platform_grants)]
    widgets = _product(
        "widgets", default_role_permissions={"Member": [_Perm.EDIT_WIDGET]}
    )

    compose_default_roles(roles, [widgets])

    assert platform_grants == [_Perm.READ_WIDGET]
