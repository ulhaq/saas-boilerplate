"""The billing module's manifest: plans, subscriptions and Stripe, plugged into
the platform like a product. Remove it from `src.products` (and its migration)
and the platform runs without plans: every feature on, no limits."""

from pathlib import Path

from src.billing import models
from src.billing.emails import BILLING_EMAIL_CAMPAIGNS, BILLING_EMAIL_SUBJECTS
from src.billing.enums import (
    BILLING_PERMISSION_DESCRIPTIONS,
    BillingAuditAction,
    BillingPermission,
)
from src.billing.hooks import (
    bill_the_new_owner,
    open_billing_account,
    refuse_deleting_a_paying_organization,
)
from src.billing.routers import billing
from src.billing.services.entitlements import PlanEntitlements
from src.billing.services.maintenance import (
    run_customer_sync_loop,
    run_stale_checkout_cleanup_loop,
    run_trial_reminder_loop,
)
from src.platform.core.hooks import HookEvent
from src.platform.core.product import ProductModule
from src.platform.core.routing import RouterMount

BILLING = ProductModule(
    name="billing",
    models=models,
    permissions=list(BillingPermission),
    permission_descriptions={**BILLING_PERMISSION_DESCRIPTIONS},
    audit_actions=list(BillingAuditAction),
    routers=[
        RouterMount(router=billing.plan_router, tags=["Billing Plans"], public=False),
        RouterMount(
            router=billing.subscription_router,
            tags=["Billing Subscriptions"],
            public=False,
        ),
        RouterMount(router=billing.usage_router, tags=["Billing Usage"], public=False),
        RouterMount(
            router=billing.webhook_router, tags=["Billing Webhooks"], public=False
        ),
    ],
    hooks={
        HookEvent.ORGANIZATION_CREATED: [open_billing_account],
        HookEvent.ORGANIZATION_DELETING: [refuse_deleting_a_paying_organization],
        HookEvent.OWNERSHIP_TRANSFERRED: [bill_the_new_owner],
    },
    worker_loops=[
        run_stale_checkout_cleanup_loop,
        run_trial_reminder_loop,
        run_customer_sync_loop,
    ],
    email_subjects=BILLING_EMAIL_SUBJECTS,
    email_campaigns=BILLING_EMAIL_CAMPAIGNS,
    email_link_keys=["billing_url"],
    template_directory=Path(__file__).resolve().parent / "templates",
    entitlements=PlanEntitlements(),
)
