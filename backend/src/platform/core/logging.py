import logging
import logging.config
import re

import structlog
from structlog.processors import CallsiteParameter
from structlog.typing import EventDict, Processor, WrappedLogger

from src.platform.core.config import settings
from src.platform.core.context import (
    auth_context_var,
    client_ip_var,
    request_id_var,
)

# Process name ("api" / "worker" / ...). Set by setup_logging() and stamped onto
# every event by add_request_context.
_service = "app"


# --- Redaction -------------------------------------------------------------

# Patterns scrubbed from every rendered message. Precompiled; applied to the
# final event string so f-strings and %-args are covered alike.
_REDACTIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"), "<jwt>"),
    (re.compile(r"(?i)bearer\s+[A-Za-z0-9._\-]+"), "Bearer <redacted>"),
    (re.compile(r"sk_[A-Za-z0-9]{8,}"), "sk_<redacted>"),
    # Key/value pairs in any common shape: `password=x`, `password: x`,
    # quoted (`token="x"`), and JSON (`"api_key": "x"`). Group 1 keeps the key
    # and separator; the value (quoted or bare, up to the next delimiter) is
    # dropped.
    (
        re.compile(
            r"(?i)(\"?\b(?:password|secret|token|api[_-]?key)\"?\s*[=:]\s*)"
            r"(\"[^\"]*\"|'[^']*'|[^\s,;]+)"
        ),
        r"\1<redacted>",
    ),
)

# Event-field keys whose *values* are replaced wholesale.
_SENSITIVE_SUBSTRINGS = (
    "password",
    "secret",
    "token",
    "authorization",
    "api_key",
    "apikey",
    "cookie",
)


def _redact_text(text: str) -> str:
    for pattern, replacement in _REDACTIONS:
        text = pattern.sub(replacement, text)
    return text


def _is_sensitive_key(key: object) -> bool:
    return isinstance(key, str) and any(s in key.lower() for s in _SENSITIVE_SUBSTRINGS)


def _redact_nested(value: object) -> object:
    """
    Walk containers, replacing any value whose key looks sensitive wholesale
    (regardless of type) and recursing into the rest. Returns fresh containers so
    the caller's logged objects are never mutated.
    """
    if isinstance(value, dict):
        return {
            key: "<redacted>" if _is_sensitive_key(key) else _redact_nested(val)
            for key, val in value.items()
        }
    if isinstance(value, list):
        return [_redact_nested(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_nested(item) for item in value)
    return value


def redact(logger: WrappedLogger, name: str, event_dict: EventDict) -> EventDict:
    """
    Processor: scrub credentials from the message and from any field whose
    key looks sensitive, recursing into nested dicts/lists.
    """
    event = event_dict.get("event")
    if isinstance(event, str):
        event_dict["event"] = _redact_text(event)
    for key, value in event_dict.items():
        if key == "event":
            continue
        if _is_sensitive_key(key):
            event_dict[key] = "<redacted>"
        else:
            event_dict[key] = _redact_nested(value)
    return event_dict


# --- Context enrichment ----------------------------------------------------


def add_request_context(
    logger: WrappedLogger, name: str, event_dict: EventDict
) -> EventDict:
    """Processor: stamp the service name and per-request context (request id,
    client ip, identity) onto every event. Reads the contextvars populated by
    the ASGI middleware; all are absent/default outside a request (the worker)."""
    event_dict["service"] = _service
    if (request_id := request_id_var.get()) is not None:
        event_dict["request_id"] = request_id
    if (client_ip := client_ip_var.get()) != "unknown":
        event_dict["client_ip"] = client_ip
    auth = auth_context_var.get() or {}
    if auth.get("org_id") is not None:
        event_dict["org_id"] = auth["org_id"]
    if auth.get("user_id") is not None:
        event_dict["user_id"] = auth["user_id"]
    return event_dict


# --- Configuration ---------------------------------------------------------

_LEVEL = settings.log_level.upper()
_JSON = settings.log_format.lower() == "json"
_SQLALCHEMY_LEVEL = "INFO" if settings.sqlalchemy_echo else "WARNING"


def _shared_processors() -> list[Processor]:
    """Processors run for both structlog-native calls and foreign records routed
    in from stdlib loggers (uvicorn, sqlalchemy, ...), so both render identically."""
    return [
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        # Surface fields passed to stdlib loggers via `extra={...}`.
        structlog.stdlib.ExtraAdder(),
        structlog.stdlib.PositionalArgumentsFormatter(),
        add_request_context,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.CallsiteParameterAdder(
            {
                CallsiteParameter.MODULE,
                CallsiteParameter.FUNC_NAME,
                CallsiteParameter.LINENO,
            }
        ),
        # Last, so it sees the fully assembled event and every added field.
        redact,
    ]


def _render_processors() -> list[Processor]:
    """Terminal processors on the stdlib handler: strip structlog bookkeeping,
    then render. JSON for prod log shipping; coloured console for local dev."""
    if _JSON:
        return [
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            # Structured tracebacks, but without frame locals: those routinely
            # hold secrets and bypass the redact processor (which runs earlier,
            # on the message only).
            structlog.processors.ExceptionRenderer(
                structlog.tracebacks.ExceptionDictTransformer(show_locals=False)
            ),
            structlog.processors.JSONRenderer(),
        ]
    return [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta,
        structlog.dev.ConsoleRenderer(colors=True),
    ]


def setup_logging(service: str) -> None:
    """Configure logging for the given process ("api" / "worker" / ...).

    structlog renders both its own loggers and plain stdlib loggers through one
    processor chain via ProcessorFormatter, so existing `logging.getLogger()`
    call sites need no changes while new code can use `structlog.get_logger()`.
    """
    global _service
    _service = service

    shared = _shared_processors()

    structlog.configure(
        processors=[
            # Lets request handlers attach ad-hoc context via
            # structlog.contextvars.bind_contextvars(...).
            structlog.contextvars.merge_contextvars,
            *shared,
            # Hand the event dict to the stdlib handler's ProcessorFormatter.
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "structlog": {
                    "()": structlog.stdlib.ProcessorFormatter,
                    "processors": _render_processors(),
                    "foreign_pre_chain": shared,
                },
            },
            "handlers": {
                "stdout": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "structlog",
                },
            },
            "loggers": {
                "uvicorn": {
                    "handlers": ["stdout"],
                    "level": "INFO",
                    "propagate": False,
                },
                "uvicorn.error": {
                    "handlers": ["stdout"],
                    "level": "INFO",
                    "propagate": False,
                },
                # Silenced: AccessLogMiddleware emits a structured access line.
                "uvicorn.access": {
                    "handlers": [],
                    "level": "WARNING",
                    "propagate": False,
                },
                "sqlalchemy.engine": {
                    "handlers": ["stdout"],
                    "level": _SQLALCHEMY_LEVEL,
                    "propagate": False,
                },
                "httpx": {"level": "WARNING"},
                "httpcore": {"level": "WARNING"},
                "aiosqlite": {"level": "WARNING"},
            },
            "root": {
                "handlers": ["stdout"],
                "level": _LEVEL,
            },
        }
    )
