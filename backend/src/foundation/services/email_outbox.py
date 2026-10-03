"""Email that must only go out once the change it reports has committed.

Callers inside a transaction (webhooks, worker jobs) queue the email with
`queue_email`; the worker's `run_email_outbox_loop` sends it afterwards, with
retries. Emails sent from a request after it commits can keep using
`send_email` via `BackgroundTasks`.
"""

import asyncio
import logging
from datetime import UTC, datetime, timedelta
from smtplib import SMTPException
from typing import Any

from jinja2 import TemplateError

from src.foundation.core.config import settings
from src.foundation.core.telemetry import track_worker_run
from src.foundation.repositories.repository_manager import RepositoryManager
from src.foundation.services.mailer import send_email

log = logging.getLogger(__name__)

MAX_ATTEMPTS = 5
BATCH_SIZE = 50


async def queue_email(
    repos: RepositoryManager,
    *,
    address: str,
    user_name: str,
    email_template: str,
    locale: str | None,
    data: dict[str, Any],
) -> None:
    """Queue an email in the caller's transaction: it is sent after commit, and
    never if the transaction rolls back. `data` must be JSON-serializable."""
    await repos.email_outbox.enqueue(
        address=address,
        user_name=user_name,
        email_template=email_template,
        locale=locale,
        data=data,
    )


async def deliver_due_emails(repos: RepositoryManager) -> int:
    """Send a batch of queued emails; returns how many were sent. A failed send
    is retried with exponential backoff, up to MAX_ATTEMPTS attempts."""
    sent = 0
    for email in await repos.email_outbox.claim_due(BATCH_SIZE, MAX_ATTEMPTS):
        try:
            await asyncio.to_thread(
                send_email,
                address=email.address,
                user_name=email.user_name,
                email_template=email.email_template,
                locale=email.locale,
                data=email.data,
            )
        except (SMTPException, OSError, TemplateError) as exc:
            retry_at = datetime.now(UTC) + timedelta(minutes=2**email.attempts)
            await repos.email_outbox.mark_failed(email, str(exc)[:1000], retry_at)
            if email.attempts >= MAX_ATTEMPTS:
                log.exception(
                    "Email gave up after %d attempts [id=%s template=%s]",
                    email.attempts,
                    email.id,
                    email.email_template,
                )
            else:
                log.warning(
                    "Email failed, retrying [id=%s attempt=%d]: %s",
                    email.id,
                    email.attempts,
                    exc,
                )
        else:
            await repos.email_outbox.mark_sent(email)
            sent += 1
    return sent


async def run_email_outbox_loop(session_factory: Any) -> None:
    """Background loop that sends queued emails. Safe to run in several
    workers: each claims different emails (SKIP LOCKED)."""
    interval = settings.email_outbox_interval_seconds
    while True:
        try:
            with track_worker_run("email_outbox", interval):
                async with session_factory() as session, session.begin():
                    sent = await deliver_due_emails(RepositoryManager(session))
                if sent:
                    log.info("Email outbox: %d email(s) sent", sent)
        except Exception:
            log.exception("Email outbox loop error")
        await asyncio.sleep(interval)
