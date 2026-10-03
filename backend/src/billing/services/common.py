from datetime import UTC, datetime

from src.billing.models.billing import Subscription


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
