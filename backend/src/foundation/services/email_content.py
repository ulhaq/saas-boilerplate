"""Locale resolution and localized subject lines for transactional emails.

Email *bodies* are localized as per-locale compiled templates under
``src/foundation/templates/emails/<locale>/<name>.html`` (all locales including ``en``).
Subject lines are localized here so callers don't carry hard-coded English strings.

Tier-1 localization: the fixed copy in all templates plus subjects. Product
packages contribute their own subject lines in their manifest, installed by
the composition root (``src.bootstrap``) and looked up after the foundation's.
"""

from collections import defaultdict
from datetime import date

from src.foundation.core import composition

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
        "verify-email-change": "Confirm your new email for {app_name}",
        "email-change-requested": "Email change requested for your {app_name} account",
        "email-changed": "The email on your {app_name} account was changed",
        "invite-user": "You've been invited to {organization_name}",
        "added-to-org": "You've been added to {organization_name}",
        "account-deletion": "Your {app_name} account has been deleted",
    },
    "da": {
        "welcome": "Velkommen til {app_name}",
        "verify-email": "Bekræft din email for {app_name}",
        "reset-password": "Nulstil din {app_name}-adgangskode",
        "verify-email-change": "Bekræft din nye email til {app_name}",
        "email-change-requested": (
            "Anmodning om ændring af email på din {app_name}-konto"
        ),
        "email-changed": "Emailen på din {app_name}-konto er ændret",
        "invite-user": "Du er inviteret til {organization_name}",
        "added-to-org": "Du er blevet tilføjet til {organization_name}",
        "account-deletion": "Din {app_name}-konto er blevet slettet",
    },
}


def _lookup(locale: str, template: str) -> str | None:
    """A product's subject line for the template, else the foundation's."""
    product = composition.current().email_subjects.get(locale, {})
    return product.get(template) or EMAIL_SUBJECTS.get(locale, {}).get(template)


def subject_for(template: str, locale: str, **values: object) -> str:
    """Return the localized, formatted subject line for a template.

    Falls back to the default locale for unknown locales/templates, and tolerates
    missing format values (renders them as empty) so a subject is always returned.
    """
    loc = normalize_locale(locale)
    template_str = (
        _lookup(loc, template) or _lookup(DEFAULT_EMAIL_LOCALE, template) or ""
    )
    # defaultdict so a missing placeholder formats to "" instead of raising.
    safe_values: defaultdict[str, object] = defaultdict(str, values)
    return template_str.format_map(safe_values)
