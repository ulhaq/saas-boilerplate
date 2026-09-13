import logging
from collections.abc import Callable

from src.platform.core.config import settings
from src.platform.schemas.contact import ContactMessageIn, ContactMessageOut
from src.platform.services.mailer import send_email

log = logging.getLogger(__name__)


class ContactService:
    """Relays public contact-form submissions to the team inbox.

    Deliberately stateless - nothing is persisted, so this service needs no
    repositories (and therefore no DB session) for an unauthenticated endpoint.
    """

    async def submit(
        self, schema_in: ContactMessageIn, schedule_task: Callable
    ) -> ContactMessageOut:
        schedule_task(
            send_email,
            address=settings.email_from_address,
            user_name=settings.email_from_name,
            email_template="contact-message",
            locale=schema_in.locale,
            # Replying to the notification reaches the person who wrote in.
            reply_to=schema_in.email,
            data={
                "sender_name": schema_in.name,
                "sender_email": schema_in.email,
                "message_subject": schema_in.subject,
                "message_body": schema_in.message,
            },
        )
        log.info("Contact message queued. [email=%s]", schema_in.email)
        return ContactMessageOut(message="Thanks - we'll get back to you shortly.")
