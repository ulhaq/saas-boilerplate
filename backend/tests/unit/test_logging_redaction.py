"""Unit tests for src/platform/core/logging.py credential redaction."""

from src.platform.core.logging import _redact_nested, _redact_text, redact

# --- _redact_text: message-string patterns ---------------------------------


def test_redacts_jwt() -> None:
    out = _redact_text("token is eyJhbGc.eyJzdWI.sig-Part_1")
    assert "eyJ" not in out
    assert "<jwt>" in out


def test_redacts_bearer_header() -> None:
    assert _redact_text("Authorization: Bearer abc.def123") == (
        "Authorization: Bearer <redacted>"
    )


def test_redacts_stripe_secret_key() -> None:
    out = _redact_text("token sk_0123456789abcdef")
    assert "0123456789abcdef" not in out
    assert "sk_<redacted>" in out


def test_redacts_key_value_equals_form() -> None:
    assert _redact_text("password=hunter2") == "password=<redacted>"


def test_redacts_key_value_colon_form() -> None:
    assert _redact_text("password: hunter2") == "password: <redacted>"


def test_redacts_quoted_value() -> None:
    out = _redact_text('token="abc123"')
    assert "abc123" not in out
    assert out == "token=<redacted>"


def test_redacts_json_style_pair_and_keeps_neighbour() -> None:
    out = _redact_text('{"api_key": "sk_live_xyz", "keep": "me"}')
    assert "sk_live_xyz" not in out
    assert '"keep": "me"' in out


def test_redaction_stops_at_delimiter() -> None:
    # The bare-value match must not swallow the following field.
    out = _redact_text("a=1, secret=topsecret, b=2")
    assert "topsecret" not in out
    assert "b=2" in out


def test_case_insensitive_key_match() -> None:
    assert _redact_text("PASSWORD=hunter2") == "PASSWORD=<redacted>"


def test_non_sensitive_text_untouched() -> None:
    msg = "user 42 logged in from 10.0.0.1"
    assert _redact_text(msg) == msg


# --- _redact_nested: key-based recursion -----------------------------------


def test_nested_dict_redacted_by_key() -> None:
    out = _redact_nested(
        {"payload": {"password": "pw", "inner": {"access_token": "tk", "ok": 1}}}
    )
    assert out == {
        "payload": {
            "password": "<redacted>",
            "inner": {"access_token": "<redacted>", "ok": 1},
        }
    }


def test_sensitive_value_redacted_regardless_of_type() -> None:
    # A non-str value under a sensitive key is still scrubbed wholesale.
    out = _redact_nested({"secret": {"nested": "data"}})
    assert out == {"secret": "<redacted>"}


def test_list_items_recursed() -> None:
    out = _redact_nested([{"api_key": "x"}, "plain", {"ok": 1}])
    assert out == [{"api_key": "<redacted>"}, "plain", {"ok": 1}]


def test_tuple_type_preserved() -> None:
    out = _redact_nested(({"token": "t"}, "keep"))
    assert out == ({"token": "<redacted>"}, "keep")
    assert isinstance(out, tuple)


def test_caller_object_not_mutated() -> None:
    original = {"meta": {"secret": "s"}}
    _redact_nested(original)
    assert original == {"meta": {"secret": "s"}}


def test_non_container_returned_as_is() -> None:
    assert _redact_nested("plain") == "plain"
    assert _redact_nested(42) == 42


# --- redact: full structlog processor --------------------------------------


def test_processor_scrubs_message_and_fields() -> None:
    out = redact(
        None,  # type: ignore[arg-type]
        "info",
        {
            "event": "login bearer abc.def.ghi",
            "authorization": "Bearer zzz",
            "meta": {"secret": "s", "fine": "ok"},
        },
    )
    assert "abc.def.ghi" not in out["event"]
    assert out["authorization"] == "<redacted>"
    assert out["meta"] == {"secret": "<redacted>", "fine": "ok"}


def test_processor_leaves_event_key_out_of_field_pass() -> None:
    # Non-string event must not raise and benign fields are preserved.
    out = redact(None, "info", {"event": {"k": "v"}, "user_id": 7})  # type: ignore[arg-type]
    assert out["user_id"] == 7
