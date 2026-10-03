"""No route uses PUT: updates are PATCH (partial), actions are POST.

PUT means "replace the whole resource with this body", which no endpoint here
does - every update changes only the fields it is sent. A route that truly
replaces a resource can be allowed below, with the reason beside it.
"""

from src.main import app
from tests.unit.test_db_session_scope import _api_routes

ALLOWED_PUT_ROUTES: set[str] = set()


def test_no_route_uses_put() -> None:
    put_routes = {
        route.path
        for route in _api_routes(app.routes)
        if "PUT" in (route.methods or ())
    }
    assert put_routes <= ALLOWED_PUT_ROUTES, (
        "Use PATCH for a partial update or POST for an action, not PUT: "
        f"{sorted(put_routes - ALLOWED_PUT_ROUTES)}"
    )
