"""`GET /v1/events`: the signed-in user's realtime event stream."""

from fastapi.testclient import TestClient

from src.foundation.core.config import settings


def test_the_event_stream_requires_a_sign_in(client: TestClient):
    rs = client.get("/v1/events")
    assert rs.status_code == 401


def test_the_event_stream_is_unbuffered_server_sent_events(
    admin_authenticated: TestClient,
    monkeypatch,
):
    monkeypatch.setattr(settings, "realtime_heartbeat_seconds", 0.05)
    monkeypatch.setattr(settings, "realtime_stream_max_seconds", 0.1)

    with admin_authenticated.stream("GET", "/v1/events") as rs:
        assert rs.status_code == 200
        assert rs.headers["content-type"].startswith("text/event-stream")
        assert rs.headers["cache-control"] == "no-cache, no-transform"
        assert rs.headers["x-accel-buffering"] == "no"
        body = "".join(rs.iter_text())

    assert body.startswith("event: ready\ndata: {}\n\n")
    assert ": keep-alive\n\n" in body
