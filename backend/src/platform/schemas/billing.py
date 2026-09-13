from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, computed_field

from src.platform.core.config import settings
from src.platform.schemas.types import ConstrainedEmail


class CheckoutIn(BaseModel):
    plan_price_id: int


class SwitchPlanIn(BaseModel):
    plan_price_id: int


class StartTrialIn(BaseModel):
    plan_price_id: int


class UpdateBillingEmailIn(BaseModel):
    billing_email: ConstrainedEmail


class PlanPriceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int
    amount: int
    currency: str
    interval: str
    interval_count: int
    is_active: bool

    @computed_field
    @property
    def trial_period_days(self) -> int | None:
        return settings.billing_trial_period_days or None

    created_at: datetime
    updated_at: datetime


class PlanSettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    key: str
    value: int | None


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    is_active: bool
    prices: list[PlanPriceOut]
    plan_settings: list[PlanSettingOut]
    created_at: datetime
    updated_at: datetime


class SubscriptionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    organization_id: int
    plan_price_id: int | None
    status: str
    current_period_start: datetime | None
    current_period_end: datetime | None
    cancel_at_period_end: bool
    canceled_at: datetime | None
    cancel_at: datetime | None
    trial_end: datetime | None
    plan_price: PlanPriceOut | None
    billing_email: str | None = None
    has_payment_method: bool = False
    trial_used: bool = False
    features: list[str] = Field(default_factory=list)
    plan_settings: list[PlanSettingOut] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class UsageItemOut(BaseModel):
    metric: str
    count: int
    limit: int | None


class UsageOut(BaseModel):
    period_start: date
    usage: list[UsageItemOut]


class CheckoutOut(BaseModel):
    checkout_url: str


class CustomerPortalOut(BaseModel):
    portal_url: str
