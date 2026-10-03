"""Tests for composing product manifests (src/bootstrap.py) and the installed
composition (src/platform/core/composition.py)."""

from enum import StrEnum
from types import ModuleType

import pytest

from src.bootstrap import (
    AUDIT_ACTION,
    RoleSpec,
    bootstrap,
    compose,
    compose_default_roles,
)
from src.platform.core import composition
from src.platform.core.entitlements import UNLIMITED
from src.platform.core.hooks import HookEvent, emit
from src.platform.core.module import Module
from src.platform.core.template import templates
from src.platform.services.email_content import subject_for
from tests.preload import WITHOUT_BILLING


class _Perm(StrEnum):
    READ_WIDGET = "read:widget"
    EDIT_WIDGET = "edit:widget"
    READ_GADGET = "read:gadget"


def _product(name: str, **kwargs) -> Module:
    return Module(name=name, models=ModuleType(name), **kwargs)


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


async def _on_plan_changed(**_: object) -> None: ...


async def _on_plan_changed_too(**_: object) -> None: ...


def test_compose_merges_hooks_subjects_and_templates_in_product_order(tmp_path):
    first = _product(
        "first",
        hooks={HookEvent.PLAN_CHANGED: [_on_plan_changed]},
        email_subjects={"en": {"widget-ready": "Widget ready"}},
        template_directory=tmp_path / "first",
    )
    second = _product(
        "second",
        hooks={HookEvent.PLAN_CHANGED: [_on_plan_changed_too]},
        email_subjects={"en": {"gadget-ready": "Gadget ready"}},
    )

    composed = compose([first, second])

    assert composed.hooks == {
        HookEvent.PLAN_CHANGED: (_on_plan_changed, _on_plan_changed_too)
    }
    assert composed.email_subjects == {
        "en": {"widget-ready": "Widget ready", "gadget-ready": "Gadget ready"}
    }
    assert composed.template_directories == [tmp_path / "first"]


def test_reading_the_composition_before_bootstrap_fails_loudly(monkeypatch):
    monkeypatch.setattr(composition, "_installed", None)

    with pytest.raises(RuntimeError, match="bootstrap"):
        composition.current()


def test_bootstrap_is_idempotent_but_a_different_composition_is_refused(
    monkeypatch,
):
    monkeypatch.setattr(composition, "_installed", None)
    bootstrap()
    installed = composition.current()
    bootstrap()
    assert composition.current() is installed

    with pytest.raises(RuntimeError, match="already installed"):
        composition.install(compose([]))


async def test_platform_code_uses_the_installed_composition(monkeypatch, tmp_path):
    (tmp_path / "emails" / "en").mkdir(parents=True)
    (tmp_path / "emails" / "en" / "widget-ready.html").write_text("<p>{{ name }}</p>")
    calls: list[dict] = []

    async def record(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(composition, "_installed", None)
    composition.install(
        compose(
            [
                _product(
                    "widgets",
                    hooks={HookEvent.PLAN_CHANGED: [record]},
                    # Products can also override a platform subject.
                    email_subjects={
                        "en": {"widget-ready": "{app_name} widget", "welcome": "Hi"}
                    },
                    template_directory=tmp_path,
                )
            ]
        )
    )

    await emit(HookEvent.PLAN_CHANGED, organization_id=1)
    assert calls == [{"organization_id": 1}]
    assert subject_for("widget-ready", "en", app_name="Acme") == "Acme widget"
    assert subject_for("welcome", "en") == "Hi"
    assert subject_for("verify-email", "en", app_name="Acme").endswith("Acme")
    rendered = templates.get_template("emails/en/widget-ready.html").render(name="<b>")
    assert rendered == "<p>&lt;b&gt;</p>"


async def test_without_a_plan_module_every_feature_is_on_with_no_limits():
    entitlements = compose([_product("widgets")]).entitlements

    assert entitlements is UNLIMITED
    assert await entitlements.has_feature(None, 1, "api_token")  # ty: ignore[invalid-argument-type]
    assert await entitlements.limit(None, 1, "seats") is None  # ty: ignore[invalid-argument-type]


def test_only_one_module_may_provide_entitlements():
    plans = _product("plans", entitlements=UNLIMITED)
    other = _product("other", entitlements=UNLIMITED)

    assert compose([plans]).entitlements is UNLIMITED
    with pytest.raises(ValueError, match="entitlements"):
        compose([plans, other])


def test_the_audit_action_enum_lists_every_installed_modules_actions():
    actions = {action.value for action in AUDIT_ACTION}

    assert AUDIT_ACTION.__name__ == "AuditAction"
    assert "auth.login" in actions
    # Billing's actions are listed exactly when billing is installed.
    assert ("billing.plan_switch" in actions) is not WITHOUT_BILLING
    assert "project.create" in actions
