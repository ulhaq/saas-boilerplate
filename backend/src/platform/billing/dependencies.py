from collections.abc import Callable
from datetime import date
from enum import StrEnum
from typing import Annotated

from fastapi import Depends

from src.platform.billing.abc import BillingProviderABC
from src.platform.billing.stripe_provider import StripeProvider
from src.platform.core.config import settings
from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import LimitExceededException
from src.platform.core.security import Auth
from src.platform.repositories.repository_manager import RepositoryManager


def get_billing_provider() -> BillingProviderABC:
    return StripeProvider(
        api_key=settings.stripe_secret_key.get_secret_value(),
        webhook_secret=settings.stripe_webhook_secret.get_secret_value(),
    )


BillingProviderDep = Annotated[BillingProviderABC, Depends(get_billing_provider)]


def _current_period_start() -> date:
    return date.today().replace(day=1)


def require_limit(metric: StrEnum) -> Callable:
    """
    FastAPI dependency factory that blocks the request with LIMIT_EXCEEDED when
    the organisation has consumed its plan allocation for `metric` this period.
    Use as a default-value dependency on the route parameter list:

        async def my_endpoint(
            _: Annotated[None, Depends(require_limit(UsageMetric.SEATS))],
            ...
        ): ...
    """

    async def _check(
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        limit = await repos.plan_setting.get_for_organization(
            current_user.organization_id, metric
        )
        if limit is None or limit.value is None:
            return
        count = await repos.plan_usage.get_count(
            current_user.organization_id, metric, _current_period_start()
        )
        if count >= limit.value:
            raise LimitExceededException()

    return _check


async def track_usage(
    repos: RepositoryManager,
    organization_id: int,
    metric: StrEnum,
) -> int:
    """Atomically increments the usage counter and returns the new count."""
    return await repos.plan_usage.increment(
        organization_id, metric, _current_period_start()
    )
