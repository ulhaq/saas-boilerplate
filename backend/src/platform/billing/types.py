from dataclasses import dataclass
from datetime import datetime


@dataclass
class ExternalProduct:
    external_id: str
    is_active: bool = True


@dataclass
class ExternalPrice:
    external_id: str
    is_active: bool = True


@dataclass
class CheckoutResult:
    checkout_url: str
    external_session_id: str


@dataclass
class CustomerPortalResult:
    portal_url: str


@dataclass
class ExternalSubscription:
    external_subscription_id: str
    external_customer_id: str
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None
    external_price_id: str | None
    cancel_at: datetime | None = None
    trial_end: datetime | None = None


@dataclass
class WebhookPayload:
    external_event_id: str
    event_type: str
    raw: dict
