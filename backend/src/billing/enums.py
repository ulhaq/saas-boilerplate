"""Billing enums: what the billing module adds to the platform's permissions,
audit actions and error codes (merged in by the composition root)."""

from enum import StrEnum

from src.platform.enums import ErrorCodeEnum


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
