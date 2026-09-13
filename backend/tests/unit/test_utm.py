from urllib.parse import parse_qs, urlsplit

from src.platform.services.utm import append_utm, apply_utm


def _params(url: str) -> dict[str, list[str]]:
    return parse_qs(urlsplit(url).query)


def test_append_utm_adds_all_three_params() -> None:
    url = append_utm(
        "https://app.example.com/settings/billing",
        campaign="trial-ending",
        medium="lifecycle",
    )
    assert _params(url) == {
        "utm_source": ["email"],
        "utm_medium": ["lifecycle"],
        "utm_campaign": ["trial-ending"],
    }
    assert urlsplit(url).path == "/settings/billing"


def test_append_utm_preserves_existing_query_params() -> None:
    url = append_utm(
        "https://app.example.com/invite?token=abc123",
        campaign="invite-user",
        medium="invite",
    )
    assert _params(url)["token"] == ["abc123"]
    assert _params(url)["utm_campaign"] == ["invite-user"]


def test_append_utm_does_not_overwrite_existing_utm() -> None:
    url = append_utm(
        "https://app.example.com/x?utm_source=newsletter",
        campaign="welcome",
        medium="lifecycle",
    )
    assert _params(url)["utm_source"] == ["newsletter"]
    assert _params(url)["utm_medium"] == ["lifecycle"]


def test_append_utm_ignores_non_http_urls() -> None:
    assert (
        append_utm("mailto:info@example.com", campaign="welcome", medium="lifecycle")
        == "mailto:info@example.com"
    )


def test_apply_utm_tags_known_keys_only() -> None:
    data = apply_utm(
        "welcome",
        {"login_url": "https://app.example.com/login", "app_name": "Acme"},
    )
    assert _params(data["login_url"])["utm_campaign"] == ["welcome"]
    assert data["app_name"] == "Acme"


def test_apply_utm_leaves_token_bearing_urls_untouched() -> None:
    verify = "https://app.example.com/verify-email?token=t"
    reset = "https://app.example.com/reset-password?token=t"
    data = apply_utm("verify-email", {"verify_url": verify})
    assert data["verify_url"] == verify
    data = apply_utm("reset-password", {"reset_url": reset})
    assert data["reset_url"] == reset


def test_apply_utm_skips_untagged_templates() -> None:
    data = {"login_url": "https://app.example.com/login"}
    assert apply_utm("account-deletion", data) == data


def test_apply_utm_returns_a_new_mapping() -> None:
    data = {"billing_url": "https://app.example.com/settings/billing"}
    tagged = apply_utm("trial-ended", data)
    assert data["billing_url"] == "https://app.example.com/settings/billing"
    assert tagged is not data
