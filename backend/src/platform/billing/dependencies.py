from datetime import date
from enum import StrEnum
from typing import Annotated

from fastapi import Depends

from src.platform.billing.abc import BillingProviderABC
from src.platform.billing.stripe_provider import StripeProvider
from src.platform.core.config import settings
from src.platform.repositories.repository_manager import RepositoryManager


def get_billing_provider() -> BillingProviderABC:
    return StripeProvider(
        api_key=settings.stripe_secret_key.get_secret_value(),
        webhook_secret=settings.stripe_webhook_secret.get_secret_value(),
    )


BillingProviderDep = Annotated[BillingProviderABC, Depends(get_billing_provider)]


def _current_period_start() -> date:
    return date.today().replace(day=1)


async def track_usage(
    repos: RepositoryManager,
    organization_id: int,
    metric: StrEnum,
) -> int:
    """Atomically increments the usage counter and returns the new count."""
    return await repos.plan_usage.increment(
        organization_id, metric, _current_period_start()
    )
