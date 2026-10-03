"""Billing enums: what the billing module adds to the platform's permissions,
audit actions and error codes (merged in by the composition root)."""

from enum import StrEnum

from src.platform.enums import ErrorCodeEnum

# The organization's current subscription: billing, or able to resume billing.
LIVE_STATUSES = ("active", "trialing", "past_due", "paused")

# The states in which a subscription's plan applies - the access policy, shared
# by the API's entitlements and the app (`SubscriptionOut.has_access`). past_due
# keeps access while Stripe retries. paused (a trial that ended without a
# payment method) is live but not entitled: the organization gets the free
# plan until it adds a card or switches, as after an uncollectible payment.
ENTITLED_STATUSES = ("active", "trialing", "past_due")


class BillingPermission(StrEnum):
    MANAGE_SUBSCRIPTION = "manage:subscription"


class BillingAuditAction(StrEnum):
    BILLING_WEBHOOK = "billing.webhook"
    BILLING_CHECKOUT_START = "billing.checkout_start"
    BILLING_TRIAL_START = "billing.trial_start"
    BILLING_DUPLICATE_SUBSCRIPTION_REFUNDED = "billing.duplicate_subscription_refunded"
    BILLING_SUBSCRIPTION_CANCEL = "billing.subscription_cancel"
    BILLING_SUBSCRIPTION_RESUME = "billing.subscription_resume"
    BILLING_PLAN_SWITCH = "billing.plan_switch"
    BILLING_EMAIL_UPDATE = "billing.email_update"


class BillingErrorCode(ErrorCodeEnum):
    BILLING_ERROR = ("billing_error", "A billing provider error occurred")
    BILLING_WEBHOOK_INVALID = (
        "billing_webhook_invalid",
        "Webhook signature verification failed",
    )
    SUBSCRIPTION_ALREADY_ACTIVE = (
        "subscription_already_active",
        "Organization already has an active subscription",
    )
    SUBSCRIPTION_NOT_FOUND = (
        "subscription_not_found",
        "No active subscription found for this organization",
    )
    TRIAL_ALREADY_USED = (
        "trial_already_used",
        "A free trial has already been used for this organization",
    )


BILLING_PERMISSION_DESCRIPTIONS: dict[BillingPermission, str] = {
    BillingPermission.MANAGE_SUBSCRIPTION: (
        "Allows managing the organization's subscription."
    ),
}
