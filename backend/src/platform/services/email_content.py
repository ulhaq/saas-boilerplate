"""Locale resolution and localized subject lines for transactional emails.

Email *bodies* are localized as per-locale compiled templates under
``src/platform/templates/emails/<locale>/<name>.html`` (all locales including ``en``).
Subject lines are localized here so callers don't carry hard-coded English strings.

Tier-1 localization: the fixed copy in all templates plus subjects. Product
packages contribute their own subject lines via ``register_email_subjects``,
called from the composition root (``src.bootstrap``).
"""

from collections import defaultdict
from datetime import date

DEFAULT_EMAIL_LOCALE = "da"
SUPPORTED_EMAIL_LOCALES: frozenset[str] = frozenset({"en", "da"})

# Full month names per locale, 1-indexed (index 0 is a placeholder). Hand-rolled
# rather than via the stdlib ``locale`` module (process-global, not thread-safe)
# or ``babel`` (a dependency for two locales). Add a row when adding a locale.
_MONTH_NAMES: dict[str, tuple[str, ...]] = {
    "en": (
        "",
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ),
    "da": (
        "",
        "januar",
        "februar",
        "marts",
        "april",
        "maj",
        "juni",
        "juli",
        "august",
        "september",
        "oktober",
        "november",
        "december",
    ),
}


def format_date(value: date, locale: str | None) -> str:
    """Format a date with localized long month names for email bodies.

    ``en`` -> ``14 June 2026``; ``da`` -> ``14. juni 2026``. Falls back to the
    default locale for unknown locales.
    """
    loc = normalize_locale(locale)
    months = _MONTH_NAMES.get(loc, _MONTH_NAMES[DEFAULT_EMAIL_LOCALE])
    month = months[value.month]
    if loc == "da":
        return f"{value.day}. {month} {value.year}"
    return f"{value.day} {month} {value.year}"


def normalize_locale(locale: str | None) -> str:
    """Map an arbitrary locale tag to a supported template locale.

    Accepts ``None``, region tags (``da-DK`` -> ``da``) and unknown languages
    (-> the default), so it's always safe to call with raw user input.
    """
    if not locale:
        return DEFAULT_EMAIL_LOCALE
    base = locale.replace("_", "-").split("-", 1)[0].strip().lower()
    return base if base in SUPPORTED_EMAIL_LOCALES else DEFAULT_EMAIL_LOCALE


# Subject lines keyed by [locale][template]. Values are ``str.format`` templates
# resolved against ``app_name`` plus whatever is in the email's ``data`` dict.
EMAIL_SUBJECTS: dict[str, dict[str, str]] = {
    "en": {
        "welcome": "Welcome to {app_name}",
        "verify-email": "Verify your email for {app_name}",
        "reset-password": "Reset your {app_name} password",
        "invite-user": "You've been invited to {organization_name}",
        "added-to-org": "You've been added to {organization_name}",
        "trial-available": "Your free {app_name} trial is still waiting",
        "trial-ending": "Your {app_name} trial is ending soon",
        "trial-ended": "Your {app_name} trial has ended",
        "payment-failed": "Payment failed for your {app_name} account",
        "payment-uncollectible": "Your {app_name} account has been downgraded",
        "payment-action-required": "Your {app_name} payment needs authentication",
        "subscription-paused": "Your {app_name} subscription has been paused",
        "subscription-resumed": "Your {app_name} subscription has been resumed",
        "account-deletion": "Your {app_name} account has been deleted",
        "contact-message": "Contact form: {message_subject}",
    },
    "da": {
        "welcome": "Velkommen til {app_name}",
        "verify-email": "Bekræft din email for {app_name}",
        "reset-password": "Nulstil din {app_name}-adgangskode",
        "invite-user": "Du er inviteret til {organization_name}",
        "added-to-org": "Du er blevet tilføjet til {organization_name}",
        "trial-available": "Din gratis {app_name}-prøveperiode venter stadig",
        "trial-ending": "Din {app_name}-prøveperiode slutter snart",
        "trial-ended": "Din {app_name}-prøveperiode er slut",
        "payment-failed": "Betaling mislykkedes for din {app_name}-konto",
        "payment-uncollectible": "Din {app_name}-konto er blevet nedgraderet",
        "payment-action-required": "Din {app_name}-betaling kræver godkendelse",
        "subscription-paused": "Dit {app_name}-abonnement er sat på pause",
        "subscription-resumed": "Dit {app_name}-abonnement er genoptaget",
        "account-deletion": "Din {app_name}-konto er blevet slettet",
        "contact-message": "Kontaktformular: {message_subject}",
    },
}


def register_email_subjects(subjects: dict[str, dict[str, str]]) -> None:
    """Merge product subject lines into the catalog, keyed [locale][template].

    Called by the composition root so the platform catalog stays product-free.
    Idempotent: re-registering the same entries is a no-op.
    """
    for locale, entries in subjects.items():
        EMAIL_SUBJECTS.setdefault(locale, {}).update(entries)


def subject_for(template: str, locale: str, **values: object) -> str:
    """Return the localized, formatted subject line for a template.

    Falls back to the default locale for unknown locales/templates, and tolerates
    missing format values (renders them as empty) so a subject is always returned.
    """
    loc = normalize_locale(locale)
    catalog = EMAIL_SUBJECTS.get(loc, EMAIL_SUBJECTS[DEFAULT_EMAIL_LOCALE])
    template_str = catalog.get(template) or EMAIL_SUBJECTS[DEFAULT_EMAIL_LOCALE].get(
        template, ""
    )
    # defaultdict so a missing placeholder formats to "" instead of raising.
    safe_values: defaultdict[str, object] = defaultdict(str, values)
    return template_str.format_map(safe_values)
