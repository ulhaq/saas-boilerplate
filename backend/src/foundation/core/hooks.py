"""Extension hooks for the generic SaaS core.

The core (auth, organizations, users) and modules such as billing emit events
at well-defined lifecycle points; other modules handle them. This keeps the
core free of imports from billing and product packages - a new module
registers its own handlers (or none) without touching core services.

Modules list their handlers in their manifest; the composition root
(`src.bootstrap`) installs them with the rest of the `Composition`. Handlers
receive keyword arguments only. Every event includes
`repos` (the request/job-scoped RepositoryManager) so handlers participate in
the caller's transaction.
"""

import logging
from collections.abc import Awaitable, Callable
from enum import StrEnum

from src.foundation.core import composition

log = logging.getLogger(__name__)

Handler = Callable[..., Awaitable[None]]


class HookEvent(StrEnum):
    # A user became a member of an organization (registration, invite,
    # or organization creation). kwargs: repos, organization_id, user_id
    MEMBER_ADDED = "member_added"
    # A user's membership in an organization was removed (removed by an
    # admin or self-deletion). kwargs: repos, organization_id, user_id
    MEMBER_REMOVED = "member_removed"
    # An organization's plan or subscription state changed (checkout,
    # switch, cancellation, webhook update). kwargs: repos, organization_id
    PLAN_CHANGED = "plan_changed"
    # A new (or restored) organization was set up, after its roles are seeded.
    # kwargs: repos, organization_id, user_id (its owner)
    ORGANIZATION_CREATED = "organization_created"
    # An organization is about to be deleted; a handler raises to refuse it.
    # kwargs: repos, organization_id
    ORGANIZATION_DELETING = "organization_deleting"
    # An organization's ownership moved to another member.
    # kwargs: repos, organization_id, user_id (the new owner)
    OWNERSHIP_TRANSFERRED = "ownership_transferred"


async def emit(event: HookEvent, **kwargs: object) -> None:
    """Run all handlers for an event, in registration order.

    Handlers run inside the caller's transaction and exceptions propagate:
    a failing handler must abort the surrounding operation rather than
    leave domain state half-applied.
    """
    for handler in composition.current().hooks.get(event, ()):
        await handler(**kwargs)
