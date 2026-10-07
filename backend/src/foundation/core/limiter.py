from slowapi import Limiter
from slowapi.util import get_remote_address

from src.foundation.core.config import settings

# Limits are per route, via `@limiter.limit(...)`. Don't add `default_limits`
# expecting slowapi's middleware to apply them: it finds a request's route by
# scanning `app.routes` for an `endpoint`, and FastAPI's included routers have
# none - so it would treat every /v1 route as exempt.
#
# Counters live in Redis (`REDIS_URL`), so a limit holds across API replicas
# and restarts. Without `REDIS_URL` (local dev, tests) they're in-process. If
# Redis goes down, slowapi counts in memory until it's back rather than
# failing the request.
limiter = Limiter(
    key_func=get_remote_address,
    enabled=settings.rate_limit_enabled,
    storage_uri=settings.redis_url or "memory://",
    key_prefix="ratelimit",
    in_memory_fallback_enabled=True,
)
