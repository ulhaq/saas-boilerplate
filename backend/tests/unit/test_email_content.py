"""Unit tests for src/platform/services/email_content.py."""

from datetime import date

from src.platform.services.email_content import (
    format_date,
    normalize_locale,
    subject_for,
)

# ---------------------------------------------------------------------------
# normalize_locale
# ---------------------------------------------------------------------------


def test_normalize_locale_none_returns_default() -> None:
    assert normalize_locale(None) == "da"


def test_normalize_locale_region_tag_strips_region() -> None:
    assert normalize_locale("da-DK") == "da"


def test_normalize_locale_unknown_returns_default() -> None:
    assert normalize_locale("zh") == "da"


def test_normalize_locale_known_locale_passthrough() -> None:
    assert normalize_locale("en") == "en"


# ---------------------------------------------------------------------------
# subject_for
# ---------------------------------------------------------------------------


def test_subject_for_formats_values_en() -> None:
    subject = subject_for("added-to-org", "en", organization_name="Acme Corp")
    assert subject == "You've been added to Acme Corp"


def test_subject_for_formats_values_da() -> None:
    subject = subject_for("added-to-org", "da", organization_name="Acme Corp")
    assert subject == "Du er blevet tilføjet til Acme Corp"


def test_subject_for_missing_placeholder_renders_empty() -> None:
    """Missing format values default to '' instead of raising KeyError."""
    subject = subject_for("added-to-org", "en")
    assert subject == "You've been added to "


def test_subject_for_unknown_template_returns_empty_string() -> None:
    subject = subject_for("nonexistent-template", "en")
    assert subject == ""


# ---------------------------------------------------------------------------
# format_date
# ---------------------------------------------------------------------------


def test_format_date_english() -> None:
    assert format_date(date(2026, 6, 14), "en") == "14 June 2026"


def test_format_date_danish() -> None:
    assert format_date(date(2026, 6, 14), "da") == "14. juni 2026"


def test_format_date_none_locale_defaults_to_danish() -> None:
    assert format_date(date(2026, 1, 1), None) == "1. januar 2026"


def test_format_date_unknown_locale_falls_back_to_default() -> None:
    assert format_date(date(2026, 12, 31), "fr") == "31. december 2026"


def test_format_date_region_tag_normalized() -> None:
    assert format_date(date(2026, 3, 9), "en-US") == "9 March 2026"
