from datetime import UTC, date, datetime

from src.billing.enums import BillingPermission
from src.billing.models.billing import Subscription
from src.billing.repositories.manager import BillingRepositoryManager
from src.platform.models.organization import Organization
from src.platform.services.email_content import format_date
from src.platform.services.email_outbox import queue_email


def _ts(ts: int | None) -> datetime | None:
    return datetime.fromtimestamp(ts, tz=UTC) if ts else None


def _get_period_field(obj: dict, field: str) -> int | None:
    """
    Extract a period timestamp field, falling back to the first subscription item.
    """
    val = obj.get(field)
    if val:
        return val
    items = obj.get("items", {}).get("data", [])
    return items[0].get(field) if items else None


def _is_active_free_sub(sub: Subscription | None) -> bool:
    return (
        sub is not None
        and sub.status == "active"
        and sub.plan_price is not None
        and sub.plan_price.amount == 0
    )


def _notification_payload(data: dict) -> dict:
    """The email data, made JSON-safe for the notification: dates as ISO
    strings (the app formats them per locale) and no absolute URLs (the app
    links to its own pages)."""
    return {
        key: value.isoformat() if isinstance(value, date) else value
        for key, value in data.items()
        if not key.endswith("_url")
    }


async def notify_subscription_managers(
    repos: BillingRepositoryManager,
    organization: Organization,
    email_template: str,
    data: dict,
) -> int:
    """Notify every member of ``organization`` who can manage the subscription:
    an in-app notification (``billing.<email_template>``) and an email, which
    the worker sends once the caller's transaction commits.

    Returns the number of recipients. Used both by webhook handlers and by the
    trial reminder loop, so it takes an Organization rather than reading one
    through a request-scoped service.
    """
    sent = 0
    for user in organization.users:
        if not any(
            p.name == BillingPermission.MANAGE_SUBSCRIPTION
            for role in user.roles
            for p in role.permissions
        ):
            continue
        # Render any date in the recipient's locale; everything else passes
        # through. Subject is derived per recipient locale when it is sent.
        localized_data = {
            key: format_date(value, user.locale) if isinstance(value, date) else value
            for key, value in data.items()
        }
        await queue_email(
            repos,
            address=user.email,
            user_name=user.name,
            email_template=email_template,
            locale=user.locale,
            data=localized_data,
        )
        await repos.notification.create(
            user_id=user.id,
            organization_id=organization.id,
            notification_type=f"billing.{email_template}",
            payload=_notification_payload(data),
        )
        sent += 1
    return sent
