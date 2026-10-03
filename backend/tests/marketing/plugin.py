"""Marketing's test fixtures - a pytest plugin `tests.preload` registers while
the marketing module is installed. Delete it with the module."""

import pytest


@pytest.fixture(autouse=True)
def mock_contact_email(mocker) -> None:
    """Prevent real SMTP calls from the contact form."""
    mocker.patch("src.marketing.services.contact.send_email")
