import logging
import time
import uuid
from collections.abc import Collection

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.datastructures import URL, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.platform.core.config import settings
from src.platform.core.context import (
    auth_context_var,
    client_ip_var,
    request_id_var,
)
from src.platform.core.error_response import ErrorResponse
from src.platform.enums import ErrorCode

log = logging.getLogger(__name__)

_ACCESS_LOG_SKIP_PATHS = frozenset({"/health"})


class AuditContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers", []))
        real_ip = (
            headers.get(b"x-real-ip", b"").decode("utf-8", errors="ignore").strip()
        )
        if real_ip:
            ip = real_ip
        else:
            client = scope.get("client")
            ip = client[0] if client else "unknown"

        incoming = (
            headers.get(b"x-request-id", b"").decode("utf-8", errors="ignore").strip()
        )
        request_id = incoming or uuid.uuid4().hex

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                message.setdefault("headers", [])
                message["headers"].append((b"x-request-id", request_id.encode("utf-8")))
            await send(message)

        ip_token = client_ip_var.set(ip)
        rid_token = request_id_var.set(request_id)
        # Mutable holder the auth dependency fills in; readable here afterwards.
        auth_token = auth_context_var.set({"org_id": None, "user_id": None})
        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            client_ip_var.reset(ip_token)
            request_id_var.reset(rid_token)
            auth_context_var.reset(auth_token)


class AccessLogMiddleware:
    """
    Emit one structured access-log line per request. Replaces uvicorn's
    opaque access logger (silenced in setup_logging) so the line carries
    queryable fields and the request context (request_id/client_ip) injected by
    AuditContextMiddleware. Must be registered inside AuditContextMiddleware and
    outside ErrorHandlingMiddleware so it observes the final status, 500s
    included.
    """

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or scope.get("path") in _ACCESS_LOG_SKIP_PATHS:
            await self.app(scope, receive, send)
            return

        status_code = 0
        start = time.perf_counter()

        async def send_wrapper(message: Message) -> None:
            nonlocal status_code
            if message["type"] == "http.response.start":
                status_code = message["status"]
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        finally:
            method = scope.get("method")
            path = scope.get("path")
            log.info(
                "%s %s -> %s",
                method,
                path,
                status_code,
                extra={
                    "method": method,
                    "path": path,
                    "status": status_code,
                    "duration_ms": round((time.perf_counter() - start) * 1000, 1),
                },
            )


class ErrorHandlingMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        response_started = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_started, send

            if message["type"] == "http.response.body":
                response_started = True

            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception as exc:  # noqa: BLE001 - last-resort error boundary
            await self.process_exception(
                scope,
                receive,
                send,
                response_started=response_started,
                exc=exc,
            )
            return
        else:
            return

    async def process_exception(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        *,
        response_started: bool,
        exc: Exception,
    ) -> None:
        query_string = (
            "?" + scope.get("query_string", b"").decode("utf-8")
            if scope.get("query_string")
            else ""
        )
        log.error(
            "%s %s%s -> %s",
            scope.get("method"),
            scope.get("path"),
            query_string,
            exc,
            exc_info=settings.log_exc_info,
        )

        response = JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=jsonable_encoder(
                ErrorResponse(
                    Request(scope),
                    msg=ErrorCode.SERVER_ERROR.description,
                    error_code=ErrorCode.SERVER_ERROR,
                ),
            ),
        )

        if not response_started:
            await response(scope, receive, send)


class SecurityHeadersMiddleware:
    """Set security headers on every HTTP response.

    HSTS and the Content-Security-Policy are sent only outside local
    development; `docs_csp` replaces `csp` on the API docs pages, whose
    CDN-hosted UI the API policy would block.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        csp: str,
        docs_csp: str,
        docs_paths: Collection[str],
    ) -> None:
        self.app = app
        self.csp = csp
        self.docs_csp = docs_csp
        self.docs_paths = docs_paths

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                headers["X-Content-Type-Options"] = "nosniff"
                headers["X-Frame-Options"] = "DENY"
                headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
                if settings.app_env != "local":
                    headers["Strict-Transport-Security"] = (
                        "max-age=31536000; includeSubDomains"
                    )
                    headers["Content-Security-Policy"] = (
                        self.docs_csp
                        if URL(scope=scope).path in self.docs_paths
                        else self.csp
                    )
            await send(message)

        await self.app(scope, receive, send_with_headers)
