"""The example product's manifest: everything it plugs into the foundation."""

from pathlib import Path

from src.example import models
from src.example.emails import (
    EXAMPLE_EMAIL_SUBJECTS,
    EXAMPLE_NOTIFICATION_CATEGORIES,
    EXAMPLE_NOTIFICATION_RULES,
)
from src.example.enums import (
    EXAMPLE_DEFAULT_ROLE_DESCRIPTIONS,
    EXAMPLE_DEFAULT_ROLE_PERMISSIONS,
    EXAMPLE_PERMISSION_DESCRIPTIONS,
    ExampleAuditAction,
    ExampleHookEvent,
    ExamplePermission,
)
from src.example.hooks import log_projects_over_plan_limit
from src.example.routers import projects
from src.example.worker import run_example_loop
from src.foundation.core.hooks import HookEvent
from src.foundation.core.module import Module
from src.foundation.core.routing import RouterMount

EXAMPLE = Module(
    name="example",
    models=models,
    permissions=list(ExamplePermission),
    permission_descriptions={**EXAMPLE_PERMISSION_DESCRIPTIONS},
    audit_actions=list(ExampleAuditAction),
    default_role_permissions=EXAMPLE_DEFAULT_ROLE_PERMISSIONS,
    default_role_descriptions=EXAMPLE_DEFAULT_ROLE_DESCRIPTIONS,
    routers=[RouterMount(router=projects.router, tags=["Projects"])],
    # Emitted by `ProjectService`; other modules may handle them.
    hook_events=list(ExampleHookEvent),
    hooks={HookEvent.ENTITLEMENTS_CHANGED: [log_projects_over_plan_limit]},
    worker_loops=[run_example_loop],
    email_subjects=EXAMPLE_EMAIL_SUBJECTS,
    template_directory=Path(__file__).resolve().parent / "templates",
    notification_categories=EXAMPLE_NOTIFICATION_CATEGORIES,
    notification_rules=EXAMPLE_NOTIFICATION_RULES,
)
