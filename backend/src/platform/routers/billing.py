from typing import Annotated

from fastapi import APIRouter, Depends, Path, Request, Response, status

from src.platform.core.cache import set_cache_control
from src.platform.core.config import settings
from src.platform.core.dependencies import authenticate, require_permission
from src.platform.core.exceptions import BillingWebhookException
from src.platform.core.limiter import limiter
from src.platform.core.security import Auth
from src.platform.enums import Permission
from src.platform.schemas.billing import (
    CheckoutIn,
    CheckoutOut,
    CustomerPortalOut,
    PlanOut,
    StartTrialIn,
    SubscriptionOut,
    SwitchPlanIn,
    UpdateBillingEmailIn,
    UsageOut,
)
from src.platform.services.billing import (
    PlanService,
    SubscriptionService,
    UsageService,
    WebhookService,
)

plan_router = APIRouter(prefix="/billing/plans")
subscription_router = APIRouter(prefix="/billing/subscriptions")
usage_router = APIRouter(prefix="/billing/usage")
webhook_router = APIRouter(prefix="/billing")


# ---------------------------------------------------------------------------
# Plan endpoints
# ---------------------------------------------------------------------------


@plan_router.get("", status_code=status.HTTP_200_OK)
async def list_plans(
    response: Response, service: Annotated[PlanService, Depends()]
) -> list[PlanOut]:
    set_cache_control(response, settings.plans_cache_max_age, private=False)
    return await service.get_all_plans()


@plan_router.get("/{plan_id}", status_code=status.HTTP_200_OK)
async def retrieve_a_plan(
    response: Response,
    service: Annotated[PlanService, Depends()],
    plan_id: Annotated[int, Path()],
) -> PlanOut:
    set_cache_control(response, settings.plans_cache_max_age, private=False)
    return await service.get_plan(plan_id)


# ---------------------------------------------------------------------------
# Subscription endpoints
# ---------------------------------------------------------------------------


@subscription_router.post("/checkout", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def start_checkout(
    request: Request,
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_SUBSCRIPTION))],
    checkout_in: CheckoutIn,
) -> CheckoutOut:
    return await service.start_checkout(checkout_in)


@subscription_router.post("/trial", status_code=status.HTTP_200_OK)
@limiter.limit("3/minute")
async def start_trial(
    request: Request,
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_SUBSCRIPTION))],
    trial_in: StartTrialIn,
) -> CheckoutOut:
    return await service.start_trial(trial_in)


@subscription_router.get("/current", status_code=status.HTTP_200_OK)
async def get_current_subscription(
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(authenticate)],
) -> SubscriptionOut:
    return await service.get_current_subscription()


@subscription_router.post("/current/cancel", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def cancel_subscription(
    request: Request,
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_SUBSCRIPTION))],
) -> SubscriptionOut:
    return await service.cancel_subscription()


@subscription_router.post("/current/resume", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def resume_subscription(
    request: Request,
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_SUBSCRIPTION))],
) -> SubscriptionOut:
    return await service.resume_subscription()


@subscription_router.post("/current/switch-plan", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def switch_plan(
    request: Request,
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_SUBSCRIPTION))],
    switch_in: SwitchPlanIn,
) -> SubscriptionOut:
    return await service.switch_plan(switch_in)


@subscription_router.put("/current", status_code=status.HTTP_200_OK)
@limiter.limit("5/minute")
async def update_billing_email(
    request: Request,
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_SUBSCRIPTION))],
    billing_email_in: UpdateBillingEmailIn,
) -> SubscriptionOut:
    await service.set_billing_email(billing_email_in)
    return await service.get_current_subscription()


@subscription_router.get("/portal", status_code=status.HTTP_200_OK)
async def get_customer_portal(
    service: Annotated[SubscriptionService, Depends()],
    _: Annotated[Auth, Depends(require_permission(Permission.MANAGE_SUBSCRIPTION))],
) -> CustomerPortalOut:
    return await service.get_customer_portal_url()


# ---------------------------------------------------------------------------
# Usage endpoints
# ---------------------------------------------------------------------------


@usage_router.get("", status_code=status.HTTP_200_OK)
async def get_current_usage(
    service: Annotated[UsageService, Depends()],
    _: Annotated[Auth, Depends(authenticate)],
) -> UsageOut:
    return await service.get_current_usage()


# ---------------------------------------------------------------------------
# Webhook endpoint
# ---------------------------------------------------------------------------


@webhook_router.post(
    "/webhook", status_code=status.HTTP_200_OK, include_in_schema=False
)
async def billing_webhook(
    request: Request, service: Annotated[WebhookService, Depends()]
) -> dict:
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature", "")
    success = await service.process_webhook(payload, sig_header)
    if not success:
        raise BillingWebhookException
    return {"received": True}
