"""Billing's emails (templates in `templates/emails/`): subject lines keyed
[locale][template], the UTM medium of each tagged template, the notification
categories, and the rules sending each email and in-app notification when a
billing event happens. Installed with the module's manifest."""

from src.billing.enums import (
    BillingHookEvent,
    BillingNotificationCategory,
    BillingPermission,
)
from src.foundation.core.module import NotificationCategory, NotificationRule

BILLING_EMAIL_SUBJECTS: dict[str, dict[str, str]] = {
    "en": {
        "trial-available": "Your free {app_name} trial is still waiting",
        "trial-ending": "Your {app_name} trial is ending soon",
        "trial-ended": "Your {app_name} trial has ended",
        "payment-failed": "Payment failed for your {app_name} account",
        "payment-uncollectible": "Your {app_name} account has been downgraded",
        "payment-action-required": "Your {app_name} payment needs authentication",
        "subscription-paused": "Your {app_name} subscription has been paused",
        "subscription-resumed": "Your {app_name} subscription has been resumed",
        "duplicate-subscription-refunded": (
            "We refunded a duplicate {app_name} subscription"
        ),
    },
    "da": {
        "trial-available": "Din gratis {app_name}-prøveperiode venter stadig",
        "trial-ending": "Din {app_name}-prøveperiode slutter snart",
        "trial-ended": "Din {app_name}-prøveperiode er slut",
        "payment-failed": "Betaling mislykkedes for din {app_name}-konto",
        "payment-uncollectible": "Din {app_name}-konto er blevet nedgraderet",
        "payment-action-required": "Din {app_name}-betaling kræver godkendelse",
        "subscription-paused": "Dit {app_name}-abonnement er sat på pause",
        "subscription-resumed": "Dit {app_name}-abonnement er genoptaget",
        "duplicate-subscription-refunded": (
            "Vi har refunderet et dobbelt {app_name}-abonnement"
        ),
    },
}

# Template -> utm_medium for the links in billing's emails (the template is the
# campaign). Templates not listed are sent untagged.
BILLING_EMAIL_CAMPAIGNS: dict[str, str] = {
    "trial-available": "lifecycle",
    "trial-ending": "lifecycle",
    "trial-ended": "lifecycle",
    "payment-failed": "dunning",
    "payment-action-required": "dunning",
    "payment-uncollectible": "dunning",
    "subscription-paused": "dunning",
    "subscription-resumed": "dunning",
}

# What subscription managers can opt out of, per channel. A failed payment
# always emails: missing it costs the organization its plan.
BILLING_NOTIFICATION_CATEGORIES = [
    NotificationCategory(
        key=BillingNotificationCategory.TRIAL,
        permission=BillingPermission.MANAGE_SUBSCRIPTION,
    ),
    NotificationCategory(
        key=BillingNotificationCategory.PAYMENT,
        email_required=True,
        permission=BillingPermission.MANAGE_SUBSCRIPTION,
    ),
    NotificationCategory(
        key=BillingNotificationCategory.SUBSCRIPTION,
        permission=BillingPermission.MANAGE_SUBSCRIPTION,
    ),
]

# Event -> (email template, category, the event kwargs the notification shows).
# The in-app notification's type is `billing.<email template>`.
_NOTIFICATIONS: dict[
    BillingHookEvent,
    tuple[str, BillingNotificationCategory, list[str]],
] = {
    BillingHookEvent.TRIAL_AVAILABLE: (
        "trial-available",
        BillingNotificationCategory.TRIAL,
        ["trial_days"],
    ),
    BillingHookEvent.TRIAL_ENDING: (
        "trial-ending",
        BillingNotificationCategory.TRIAL,
        ["trial_end_date", "has_payment_method"],
    ),
    BillingHookEvent.TRIAL_ENDED: (
        "trial-ended",
        BillingNotificationCategory.TRIAL,
        [],
    ),
    BillingHookEvent.PAYMENT_FAILED: (
        "payment-failed",
        BillingNotificationCategory.PAYMENT,
        [],
    ),
    BillingHookEvent.PAYMENT_ACTION_REQUIRED: (
        "payment-action-required",
        BillingNotificationCategory.PAYMENT,
        [],
    ),
    BillingHookEvent.PAYMENT_UNCOLLECTIBLE: (
        "payment-uncollectible",
        BillingNotificationCategory.PAYMENT,
        [],
    ),
    BillingHookEvent.SUBSCRIPTION_PAUSED: (
        "subscription-paused",
        BillingNotificationCategory.SUBSCRIPTION,
        [],
    ),
    BillingHookEvent.SUBSCRIPTION_RESUMED: (
        "subscription-resumed",
        BillingNotificationCategory.SUBSCRIPTION,
        [],
    ),
    BillingHookEvent.DUPLICATE_SUBSCRIPTION_REFUNDED: (
        "duplicate-subscription-refunded",
        BillingNotificationCategory.SUBSCRIPTION,
        [],
    ),
}

# Each event notifies the organization's subscription managers, carried out by
# the foundation's notification service - billing's services only emit events.
BILLING_NOTIFICATION_RULES = [
    NotificationRule(
        event=event,
        category=category,
        notification_type=f"billing.{template}",
        email_template=template,
        recipients=BillingPermission.MANAGE_SUBSCRIPTION,
        data=data,
        links={"billing_url": "/settings/billing"},
    )
    for event, (template, category, data) in _NOTIFICATIONS.items()
]
