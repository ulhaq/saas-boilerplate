"""Billing's emails (templates in `templates/emails/`): subject lines keyed
[locale][template], and the UTM medium of each tagged template. Installed with
the module's manifest."""

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
