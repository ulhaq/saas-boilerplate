from slowapi import Limiter
from slowapi.util import get_remote_address

from src.foundation.core.config import settings

# Limits are per route, via `@limiter.limit(...)`. Don't add `default_limits`
# expecting slowapi's middleware to apply them: it finds a request's route by
# scanning `app.routes` for an `endpoint`, and FastAPI's included routers have
# none - so it would treat every /v1 route as exempt.
limiter = Limiter(key_func=get_remote_address, enabled=settings.rate_limit_enabled)
