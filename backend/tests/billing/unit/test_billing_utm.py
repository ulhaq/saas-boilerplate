"""UTM tagging of billing's emails (its manifest campaigns and link keys)."""

from urllib.parse import parse_qs, urlsplit

from src.platform.services.utm import apply_utm


def _params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


def test_apply_utm_tags_the_installed_modules_emails() -> None:
    """Billing lists its templates and the `billing_url` link key."""
    data = apply_utm(
        "payment-failed",
        {"billing_url": "https://app.example.com/settings/billing"},
    )
    params = _params(data["billing_url"])
    assert params["utm_campaign"] == ["payment-failed"]
    assert params["utm_medium"] == ["dunning"]
