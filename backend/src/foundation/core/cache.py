from fastapi import Response


def set_cache_control(
    response: Response,
    max_age: int,
    *,
    private: bool = True,
) -> None:
    """Set a ``Cache-Control`` header on an outgoing response.

    Use ``private`` (the default) for per-user or per-org responses so shared
    caches (CDNs/proxies) never store them; only the end user's browser may.
    """
    scope = "private" if private else "public"
    response.headers["Cache-Control"] = f"{scope}, max-age={max_age}"
