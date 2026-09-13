import logging
import time
import uuid

from fastapi import Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from src.platform.core.config import settings
from src.platform.core.context import (
    auth_context_var,
    client_ip_var,
    request_id_var,
)
from src.platform.enums import ErrorCode
from src.platform.schemas.common import ErrorResponse

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
            return
        except Exception as exc:
            await self.process_exception(scope, receive, send, response_started, exc)
            return

    async def process_exception(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
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
                )
            ),
        )

        if not response_started:
            await response(scope, receive, send)
