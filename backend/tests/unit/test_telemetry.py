"""Telemetry helpers: worker-run tracking, webhook counter, trace ids in logs.

Installs in-memory tracer/meter providers once for this process; the module's
instruments are created against the global proxies and bind to them.
"""

import time

import pytest
from opentelemetry import metrics, trace
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import InMemoryMetricReader
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor
from opentelemetry.sdk.trace.export.in_memory_span_exporter import (
    InMemorySpanExporter,
)
from opentelemetry.trace import StatusCode

from src.platform.core.logging import add_trace_context
from src.platform.core.telemetry import record_webhook_event, track_worker_run

_reader = InMemoryMetricReader()
_spans = InMemorySpanExporter()


@pytest.fixture(scope="module", autouse=True)
def _providers() -> None:
    metrics.set_meter_provider(MeterProvider(metric_readers=[_reader]))
    tracer_provider = TracerProvider()
    tracer_provider.add_span_processor(SimpleSpanProcessor(_spans))
    trace.set_tracer_provider(tracer_provider)


def _points(name: str) -> list:
    data = _reader.get_metrics_data()
    if data is None:  # nothing recorded yet
        return []
    return [
        point
        for resource_metrics in data.resource_metrics
        for scope_metrics in resource_metrics.scope_metrics
        for metric in scope_metrics.metrics
        if metric.name == name
        for point in metric.data.data_points
    ]


def _value(name: str, **attributes: str) -> float:
    for point in _points(name):
        if dict(point.attributes) == attributes:
            return point.value
    return 0


def test_track_worker_run_success_records_metrics_and_span():
    before = _value("worker.runs", worker="t_ok", outcome="success")

    with track_worker_run("t_ok", 60):
        pass

    assert _value("worker.runs", worker="t_ok", outcome="success") == before + 1
    assert _value("worker.interval", worker="t_ok") == 60
    assert time.time() - _value("worker.last_success", worker="t_ok") < 5
    span = next(s for s in _spans.get_finished_spans() if s.name == "worker t_ok")
    assert span.status.status_code != StatusCode.ERROR


def test_track_worker_run_error_reraises_and_keeps_last_success():
    with pytest.raises(RuntimeError), track_worker_run("t_err", 60):
        raise RuntimeError("boom")

    assert _value("worker.runs", worker="t_err", outcome="error") == 1
    # never succeeded, so the heartbeat alert sees no last-success point
    assert not [
        p for p in _points("worker.last_success") if p.attributes["worker"] == "t_err"
    ]
    span = next(s for s in _spans.get_finished_spans() if s.name == "worker t_err")
    assert span.status.status_code == StatusCode.ERROR


def test_record_webhook_event_counts_by_type_and_outcome():
    record_webhook_event("invoice.paid", "processed")
    record_webhook_event("invoice.paid", "processed")
    record_webhook_event("invoice.paid", "failed")

    assert (
        _value("billing.webhook.events", event_type="invoice.paid", outcome="processed")
        == 2
    )
    assert (
        _value("billing.webhook.events", event_type="invoice.paid", outcome="failed")
        == 1
    )


def test_add_trace_context_only_inside_a_span():
    assert "trace_id" not in add_trace_context(None, "info", {})

    with trace.get_tracer("test").start_as_current_span("s") as span:
        event = add_trace_context(None, "info", {})

    context = span.get_span_context()
    assert event["trace_id"] == format(context.trace_id, "032x")
    assert event["span_id"] == format(context.span_id, "016x")
