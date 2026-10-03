"""Billing metrics, on the same meter provider as the foundation's
(`src.foundation.core.telemetry`)."""

from opentelemetry import metrics

_meter = metrics.get_meter("src.billing")

_webhook_events = _meter.create_counter(
    "billing.webhook.events",
    unit="{event}",
    description="Stripe webhook events by type and outcome",
)


def record_webhook_event(event_type: str, outcome: str) -> None:
    """outcome: processed / duplicate / retry (transient, Stripe retries) /
    failed (permanent, acknowledged)."""
    _webhook_events.add(1, {"event_type": event_type, "outcome": outcome})
