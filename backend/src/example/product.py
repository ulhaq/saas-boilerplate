"""The example product's manifest: everything it plugs into the platform."""

from src.example import models
from src.example.enums import (
    EXAMPLE_DEFAULT_ROLE_DESCRIPTIONS,
    EXAMPLE_DEFAULT_ROLE_PERMISSIONS,
    EXAMPLE_PERMISSION_DESCRIPTIONS,
    ExamplePermission,
)
from src.example.hooks import log_projects_over_plan_limit
from src.example.routers import projects
from src.example.worker import run_example_loop
from src.platform.core.hooks import HookEvent
from src.platform.core.product import ProductModule, ProductRouter

EXAMPLE = ProductModule(
    name="example",
    models=models,
    permissions=list(ExamplePermission),
    permission_descriptions={**EXAMPLE_PERMISSION_DESCRIPTIONS},
    default_role_permissions=EXAMPLE_DEFAULT_ROLE_PERMISSIONS,
    default_role_descriptions=EXAMPLE_DEFAULT_ROLE_DESCRIPTIONS,
    routers=[ProductRouter(router=projects.router, tags=["Projects"])],
    hooks={HookEvent.PLAN_CHANGED: [log_projects_over_plan_limit]},
    worker_loops=[run_example_loop],
    # A product that sends its own email also sets:
    #   email_subjects=EXAMPLE_EMAIL_SUBJECTS,
    #   template_directory=Path(__file__).resolve().parent / "templates",
)
