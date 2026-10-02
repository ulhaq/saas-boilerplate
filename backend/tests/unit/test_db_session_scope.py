"""Every route must get its DB session with scope="function" (via `DbSession`).

The default "request" scope commits only after the response and its background
tasks have been sent - see `DbSession` in core/database.py.
"""

from collections.abc import Iterable, Iterator

from fastapi.dependencies.models import Dependant
from fastapi.routing import APIRoute
from starlette.routing import BaseRoute

from src.main import app
from src.platform.core.database import get_db


def _api_routes(routes: Iterable[BaseRoute]) -> Iterator[APIRoute]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif (router := getattr(route, "original_router", None)) is not None:
            # FastAPI keeps included routers as lazy wrappers, not APIRoutes.
            yield from _api_routes(router.routes)


def _session_dependants(dependant: Dependant) -> Iterator[Dependant]:
    for sub in dependant.dependencies:
        if sub.call is get_db:
            yield sub
        yield from _session_dependants(sub)


def test_every_route_commits_before_the_response() -> None:
    routes = list(_api_routes(app.routes))
    # The walk must reach every route - at least every operation in the schema
    # (some routes are hidden from it) - or the check below proves nothing.
    operations = sum(len(item) for item in app.openapi()["paths"].values())
    assert len(routes) >= operations

    for route in routes:
        for dependant in _session_dependants(route.dependant):
            assert dependant.computed_scope == "function", (
                f"{route.path}: depend on the session via DbSession, "
                "not Depends(get_db)"
            )
