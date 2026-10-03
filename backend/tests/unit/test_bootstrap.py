"""Tests for composing product manifests (src/bootstrap.py) and the installed
composition (src/foundation/core/composition.py)."""

from dataclasses import replace
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
from src.foundation import enums as core_enums
from src.foundation.core import composition
from src.foundation.core.entitlements import UNLIMITED
from src.foundation.core.hooks import HookEvent, emit
from src.foundation.core.module import Module, NotificationCategory, NotificationRule
from src.foundation.core.template import templates
from src.foundation.services.email_content import subject_for
from src.foundation.services.notification import RuleHandler
from src.products import MODULES


class _Perm(StrEnum):
    READ_WIDGET = "read:widget"
    EDIT_WIDGET = "edit:widget"
    READ_GADGET = "read:gadget"


def _product(name: str, **kwargs) -> Module:
    return Module(name=name, models=ModuleType(name), **kwargs)


def test_compose_default_roles_adds_each_products_grants():
    roles: list[RoleSpec] = [("Member", "Default member", [_Perm.READ_WIDGET])]
    widgets = _product(
        "widgets",
        default_role_permissions={"Member": [_Perm.EDIT_WIDGET]},
    )
    gadgets = _product(
        "gadgets",
        default_role_permissions={"Member": [_Perm.READ_GADGET]},
    )

    assert compose_default_roles(roles, [widgets, gadgets]) == [
        (
            "Member",
            "Default member",
            [_Perm.READ_WIDGET, _Perm.EDIT_WIDGET, _Perm.READ_GADGET],
        ),
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


def test_compose_default_roles_does_not_mutate_foundation_roles():
    foundation_grants: list[StrEnum] = [_Perm.READ_WIDGET]
    roles: list[RoleSpec] = [("Member", "Default member", foundation_grants)]
    widgets = _product(
        "widgets",
        default_role_permissions={"Member": [_Perm.EDIT_WIDGET]},
    )

    compose_default_roles(roles, [widgets])

    assert foundation_grants == [_Perm.READ_WIDGET]


async def _on_entitlements_changed(**_: object) -> None: ...


async def _on_entitlements_changed_too(**_: object) -> None: ...


def test_compose_merges_hooks_subjects_and_templates_in_product_order(tmp_path):
    first = _product(
        "first",
        hooks={HookEvent.ENTITLEMENTS_CHANGED: [_on_entitlements_changed]},
        email_subjects={"en": {"widget-ready": "Widget ready"}},
        template_directory=tmp_path / "first",
    )
    second = _product(
        "second",
        hooks={HookEvent.ENTITLEMENTS_CHANGED: [_on_entitlements_changed_too]},
        email_subjects={"en": {"gadget-ready": "Gadget ready"}},
    )

    composed = compose([first, second])

    assert composed.hooks == {
        HookEvent.ENTITLEMENTS_CHANGED: (
            _on_entitlements_changed,
            _on_entitlements_changed_too,
        ),
    }
    assert composed.email_subjects == {
        "en": {"widget-ready": "Widget ready", "gadget-ready": "Gadget ready"},
    }
    assert composed.template_directories == [tmp_path / "first"]


class _WidgetEvent(StrEnum):
    WIDGET_BUILT = "widgets.widget_built"


class _ClashingEvent(StrEnum):
    WIDGET_BUILT = "widgets.widget_built"


async def _on_widget_built(**_: object) -> None: ...


def test_compose_lets_a_module_handle_another_modules_hook_event():
    widgets = _product("widgets", hook_events=list(_WidgetEvent))
    gadgets = _product("gadgets", hooks={_WidgetEvent.WIDGET_BUILT: [_on_widget_built]})

    composed = compose([widgets, gadgets])

    assert composed.hooks == {_WidgetEvent.WIDGET_BUILT: (_on_widget_built,)}


def test_compose_refuses_a_handler_for_an_undeclared_hook_event():
    gadgets = _product("gadgets", hooks={_WidgetEvent.WIDGET_BUILT: [_on_widget_built]})

    with pytest.raises(ValueError, match="no installed module declares"):
        compose([gadgets])


def test_compose_refuses_a_handler_keyed_by_an_equal_but_different_event():
    widgets = _product("widgets", hook_events=list(_WidgetEvent))
    gadgets = _product(
        "gadgets",
        hooks={_ClashingEvent.WIDGET_BUILT: [_on_widget_built]},
    )

    with pytest.raises(ValueError, match="no installed module declares"):
        compose([widgets, gadgets])


@pytest.mark.parametrize(
    "second_events",
    [list(_ClashingEvent), [HookEvent.ENTITLEMENTS_CHANGED]],
    ids=["another module's", "the foundation's"],
)
def test_compose_refuses_a_hook_event_value_declared_twice(second_events):
    widgets = _product("widgets", hook_events=list(_WidgetEvent))
    clashing = _product("clashing", hook_events=second_events)

    with pytest.raises(ValueError, match="declared twice"):
        compose([widgets, clashing])


class _Category(StrEnum):
    WIDGETS = "widgets.widgets"


_RULE = NotificationRule(
    event=_WidgetEvent.WIDGET_BUILT,
    category=_Category.WIDGETS,
    notification_type="widgets.widget-built",
    email_template="widget-built",
    recipients=_Perm.READ_WIDGET,
    exclude_user="builder_id",
    data=["widget_name"],
)


def _widgets(*rules: NotificationRule) -> Module:
    return _product(
        "widgets",
        hook_events=list(_WidgetEvent),
        notification_categories=[NotificationCategory(key=_Category.WIDGETS)],
        notification_rules=list(rules),
    )


def test_compose_subscribes_a_notification_rule_to_its_event():
    rule = _RULE

    composed = compose([_widgets(rule)])

    assert composed.hooks == {_WidgetEvent.WIDGET_BUILT: (RuleHandler(rule),)}
    # Composing again gives an equal composition, so bootstrap stays idempotent.
    assert compose([_widgets(rule)]) == composed


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"event": _ClashingEvent.WIDGET_BUILT}, "hook event"),
        ({"category": core_enums.Permission.READ_USER}, "category"),
    ],
    ids=["undeclared event", "undeclared category"],
)
def test_compose_refuses_a_notification_rule_it_cannot_carry_out(overrides, message):
    with pytest.raises(ValueError, match=f"{message}.*no installed module declares"):
        compose([_widgets(replace(_RULE, **overrides))])


async def test_a_notification_rule_refuses_an_event_lacking_its_data():
    with pytest.raises(TypeError, match=r"lacks \['builder_id', 'widget_name'\]"):
        await RuleHandler(_RULE)(repos=None, organization_id=1)


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


async def test_foundation_code_uses_the_installed_composition(monkeypatch, tmp_path):
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
                    hook_events=list(_WidgetEvent),
                    hooks={
                        HookEvent.ENTITLEMENTS_CHANGED: [record],
                        _WidgetEvent.WIDGET_BUILT: [record],
                    },
                    # Products can also override a foundation subject.
                    email_subjects={
                        "en": {"widget-ready": "{app_name} widget", "welcome": "Hi"},
                    },
                    template_directory=tmp_path,
                ),
            ],
        ),
    )

    await emit(HookEvent.ENTITLEMENTS_CHANGED, organization_id=1)
    await emit(_WidgetEvent.WIDGET_BUILT, widget_id=2)
    assert calls == [{"organization_id": 1}, {"widget_id": 2}]
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
    assert {action.value for action in core_enums.AuditAction} <= actions
    # Exactly the installed modules' actions - whichever modules those are.
    for module in MODULES:
        assert {action.value for action in module.audit_actions} <= actions
    assert len(actions) == len(core_enums.AuditAction) + sum(
        len(module.audit_actions) for module in MODULES
    )
