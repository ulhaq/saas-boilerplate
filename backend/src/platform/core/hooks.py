"""Extension hooks for the generic SaaS core.

The core (auth, organizations, users, billing) emits events at well-defined
lifecycle points; domain modules register async handlers for them. This keeps
the core free of imports from product-specific packages - a new product
registers its own handlers (or none) without touching core services.

Handlers are registered at process startup by the composition root
(`src.bootstrap`) and receive keyword arguments only. Every event includes
`repos` (the request/job-scoped RepositoryManager) so handlers participate in
the caller's transaction.
"""

import logging
from collections.abc import Awaitable, Callable
from enum import StrEnum

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


_registry: dict[HookEvent, list[Handler]] = {}


def register(event: HookEvent, handler: Handler) -> None:
    handlers = _registry.setdefault(event, [])
    if handler in handlers:
        return
    handlers.append(handler)


def clear() -> None:
    """Remove all registered handlers - intended for test isolation."""
    _registry.clear()


async def emit(event: HookEvent, **kwargs: object) -> None:
    """Run all handlers for an event, in registration order.

    Handlers run inside the caller's transaction and exceptions propagate:
    a failing handler must abort the surrounding operation rather than
    leave domain state half-applied.
    """
    for handler in _registry.get(event, []):
        await handler(**kwargs)
