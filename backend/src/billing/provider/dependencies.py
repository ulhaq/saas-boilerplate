from typing import Annotated

from fastapi import Depends

from src.billing.config import billing_settings
from src.billing.provider.abc import BillingProviderABC
from src.billing.provider.stripe_provider import StripeProvider


def get_billing_provider() -> BillingProviderABC:
    return StripeProvider(
        api_key=billing_settings.stripe_secret_key.get_secret_value(),
        webhook_secret=billing_settings.stripe_webhook_secret.get_secret_value(),
    )


BillingProviderDep = Annotated[BillingProviderABC, Depends(get_billing_provider)]
