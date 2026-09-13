"""UTM tagging for links embedded in outbound email.

Campaign tags are applied centrally in :func:`apply_utm`, called from
``send_email``, so templates keep bare URL variables and no MJML needs
recompiling when tagging changes.

Token-bearing links (``verify_url``, ``reset_url``) are deliberately absent
from :data:`_URL_KEYS`: they are security-critical, carry no marketing
question worth answering, and extra query params invite truncation by
mail-client link scanners.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

UTM_SOURCE = "email"

# Links tagged from top-level template data. Nested or pre-rendered URLs (e.g.
# per-item links inside a digest) call append_utm at their build site instead.
_URL_KEYS = frozenset({"billing_url", "login_url", "invite_url"})

# Template name doubles as the campaign, so there is only one naming scheme to
# keep in sync. A template absent from this map is never tagged.
_MEDIUM_BY_TEMPLATE = {
    "trial-available": "lifecycle",
    "trial-ending": "lifecycle",
    "trial-ended": "lifecycle",
    "welcome": "lifecycle",
    "payment-failed": "dunning",
    "payment-action-required": "dunning",
    "payment-uncollectible": "dunning",
    "subscription-paused": "dunning",
    "subscription-resumed": "dunning",
    "added-to-org": "invite",
    "invite-user": "invite",
}


def append_utm(url: str, *, campaign: str, medium: str) -> str:
    """Return ``url`` with utm_source/medium/campaign appended.

    Existing query params are preserved and any utm_* already present wins, so
    a caller that tagged a URL itself is never overwritten. A non-http(s) or
    unparseable value is returned unchanged.
    """
    parts = urlsplit(url)
    if parts.scheme not in ("http", "https"):
        return url

    params = parse_qsl(parts.query, keep_blank_values=True)
    present = {key for key, _ in params}
    for key, value in (
        ("utm_source", UTM_SOURCE),
        ("utm_medium", medium),
        ("utm_campaign", campaign),
    ):
        if key not in present:
            params.append((key, value))

    return urlunsplit(parts._replace(query=urlencode(params)))


def apply_utm(email_template: str, data: dict) -> dict:
    """Return ``data`` with known URL keys UTM-tagged for this template.

    Returns the mapping unchanged when the template opts out of tagging.
    """
    medium = _MEDIUM_BY_TEMPLATE.get(email_template)
    if medium is None:
        return data

    tagged = {
        key: append_utm(value, campaign=email_template, medium=medium)
        for key, value in data.items()
        if key in _URL_KEYS and isinstance(value, str)
    }
    return data | tagged if tagged else data
