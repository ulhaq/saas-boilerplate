"""Example product handlers for the platform lifecycle hooks.

Listed in `src.example.product` and registered by the composition root
(`src.bootstrap`). Handlers receive keyword arguments only, including the
platform ``RepositoryManager`` as ``repos``; wrap its session in
``ExampleRepositoryManager(repos.db)`` to reach product repositories inside the
caller's transaction.
"""

import logging

from src.example.enums import ExampleUsageMetric
from src.example.repositories.manager import ExampleRepositoryManager
from src.platform.repositories.repository_manager import RepositoryManager

log = logging.getLogger(__name__)


async def log_projects_over_plan_limit(
    *, repos: RepositoryManager, organization_id: int
) -> None:
    """After a plan change, report organizations holding more projects than the
    new plan allows. Existing projects are kept; creating more is blocked by
    the capacity check in ``ProjectService``."""
    limit = await repos.plan_setting.get_for_organization(
        organization_id, ExampleUsageMetric.PROJECTS
    )
    if limit is None or limit.value is None:
        return
    project_repo = ExampleRepositoryManager(repos.db).project
    project_repo.set_organization_scope(organization_id)
    count = await project_repo.count()
    if count > limit.value:
        log.info(
            "Organization %d holds %d projects, above its plan limit of %d",
            organization_id,
            count,
            limit.value,
        )
