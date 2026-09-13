import logging
import time
from email.headerregistry import Address
from email.message import EmailMessage
from smtplib import SMTP, SMTPException

from jinja2 import TemplateNotFound

from src.platform.core.config import settings
from src.platform.core.template import templates
from src.platform.services.email_content import (
    DEFAULT_EMAIL_LOCALE,
    normalize_locale,
    subject_for,
)
from src.platform.services.utm import apply_utm

log = logging.getLogger(__name__)

_MAX_EMAIL_ATTEMPTS = 3
_EMAIL_RETRY_BASE = 2.0


def send_email(
    *,
    address: str,
    user_name: str,
    email_template: str,
    locale: str | None = None,
    subject: str | None = None,
    reply_to: str | None = None,
    data: dict | None = None,
) -> None:
    if data is None:
        data = {}
    # Base fields take precedence over caller data so app_name etc. can't be
    # accidentally shadowed.
    data = data | {
        "app_name": settings.app_name,
        "app_url": settings.app_url,
        "info_email": settings.email_from_address,
        "user_name": user_name,
    }
    data = apply_utm(email_template, data)

    loc = normalize_locale(locale)
    if subject is None:
        subject = subject_for(email_template, loc, **data)

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = Address(
        settings.email_from_name, addr_spec=settings.email_from_address
    )
    msg["To"] = Address(user_name, addr_spec=address)
    if reply_to:
        msg["Reply-To"] = reply_to

    msg.set_content(
        "This is an HTML email. Please view it in an HTML-compatible client."
    )
    msg.add_alternative(_render_email(email_template, loc, data), subtype="html")

    _smtp_send(msg)
    log.info(
        "Email sent. [template=%s, locale=%s, address=%s]", email_template, loc, address
    )


def _render_email(email_template: str, locale: str, data: dict) -> str:
    """Render the compiled HTML for a template in the given locale.

    All locales live under ``emails/<locale>/``; English (``en``) is the
    canonical fallback. A missing localized file falls back to English rather
    than failing the send.
    """
    candidates = []
    if locale != DEFAULT_EMAIL_LOCALE:
        candidates.append(f"emails/{locale}/{email_template}.html")
    candidates.append(f"emails/{DEFAULT_EMAIL_LOCALE}/{email_template}.html")

    for path in candidates:
        try:
            return templates.get_template(path).render(**data)
        except TemplateNotFound:
            continue
    raise TemplateNotFound(f"emails/{DEFAULT_EMAIL_LOCALE}/{email_template}.html")


def _smtp_send(msg: EmailMessage) -> None:
    for attempt in range(1, _MAX_EMAIL_ATTEMPTS + 1):
        try:
            with SMTP(settings.email_host, settings.email_port) as smtp:
                if settings.email_tls:
                    smtp.ehlo()
                    if smtp.has_extn("STARTTLS"):
                        smtp.starttls()
                        smtp.ehlo()
                if settings.email_user and settings.email_password:
                    smtp.login(settings.email_user, settings.email_password)
                smtp.send_message(msg)
            return
        except (SMTPException, OSError) as exc:
            if attempt == _MAX_EMAIL_ATTEMPTS:
                raise
            delay = _EMAIL_RETRY_BASE**attempt
            log.warning(
                "SMTP error (attempt %d/%d): %s - retrying in %.0fs",
                attempt,
                _MAX_EMAIL_ATTEMPTS,
                exc,
                delay,
            )
            time.sleep(delay)
