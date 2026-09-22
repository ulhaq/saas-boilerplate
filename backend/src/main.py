import logging
from collections.abc import AsyncGenerator, Callable
from contextlib import asynccontextmanager
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware import Middleware
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.bootstrap import bootstrap
from src.example.routers import projects
from src.platform.core.config import settings
from src.platform.core.database import get_db
from src.platform.core.exceptions import ClientException
from src.platform.core.limiter import limiter
from src.platform.core.logging import setup_logging
from src.platform.core.middlewares import (
    AccessLogMiddleware,
    AuditContextMiddleware,
    ErrorHandlingMiddleware,
)
from src.platform.core.telemetry import instrument_app, setup_telemetry
from src.platform.enums import ErrorCode
from src.platform.routers import (
    api_token,
    audit_log,
    auth,
    billing,
    contact,
    invitation,
    notification,
    organization,
    permission,
    role,
    user,
    waitlist,
)
from src.platform.schemas.common import (
    ErrorResponse,
    ValidationDetail,
    ValidationErrorResponse,
)

setup_logging("api")
setup_telemetry("api")

log = logging.getLogger(__name__)

bootstrap()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    yield


app = FastAPI(
    lifespan=lifespan,
    title=settings.app_name,
    debug=settings.app_debug,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=settings.allow_origins,
            allow_credentials=settings.allow_credentials,
            allow_methods=["*"],
            allow_headers=["*"],
        ),
        Middleware(AuditContextMiddleware),
        Middleware(AccessLogMiddleware),
        Middleware(ErrorHandlingMiddleware),
        Middleware(SlowAPIMiddleware),
    ],
)

app.state.limiter = limiter
instrument_app(app)


API_CSP = (
    "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data:; connect-src 'self'"
)

# Swagger UI / ReDoc are served from a CDN and bootstrap themselves with an
# inline <script>, so the API policy above would blank the page.
DOCS_CSP = (
    "default-src 'self'; "
    "script-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; "
    "style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net "
    "https://fonts.googleapis.com; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdn.jsdelivr.net; "
    "img-src 'self' data: https://fastapi.tiangolo.com https://cdn.jsdelivr.net; "
    "connect-src 'self'; worker-src 'self' blob:"
)

DOCS_PATHS = {
    path
    for path in (app.docs_url, app.redoc_url, app.swagger_ui_oauth2_redirect_url)
    if path
}


@app.middleware("http")
async def add_security_headers(
    request: Request, call_next: Callable[..., Any]
) -> Response:
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    if settings.app_env != "local":
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            DOCS_CSP if request.url.path in DOCS_PATHS else API_CSP
        )
    return response


@app.exception_handler(RateLimitExceeded)
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> Response:
    return _rate_limit_exceeded_handler(request, exc)


@app.exception_handler(HTTPException)
async def handle_http_exception(request: Request, exc: HTTPException) -> JSONResponse:
    log.info("%s: %s", exc, request.url, exc_info=settings.log_exc_info)

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ErrorResponse(
                request,
                error_code=ErrorCode.SERVER_ERROR
                if exc.status_code != 401
                else ErrorCode.UNAUTHORIZED,
                msg=exc.detail,
            )
        ),
        headers=exc.headers,
    )


@app.exception_handler(ClientException)
async def handle_client_exception(
    request: Request, exc: ClientException
) -> JSONResponse:
    log.info("%s: %s", exc, request.url, exc_info=settings.log_exc_info)

    return JSONResponse(
        status_code=exc.status_code,
        content=jsonable_encoder(
            ErrorResponse(request, error_code=exc.error_code, msg=exc.detail)
        ),
        headers=exc.headers,
    )


@app.exception_handler(IntegrityError)
async def handle_integrity_error(request: Request, exc: IntegrityError) -> JSONResponse:
    log.info("%s: %s", exc, request.url, exc_info=settings.log_exc_info)
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content=jsonable_encoder(
            ErrorResponse(
                request,
                error_code=ErrorCode.RESOURCE_ALREADY_EXISTS,
                msg=ErrorCode.RESOURCE_ALREADY_EXISTS.description,
            )
        ),
    )


@app.exception_handler(ValidationError)
async def handle_validation_error(
    request: Request, exc: ValidationError
) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            ValidationErrorResponse(
                request,
                error_code=ErrorCode.VALIDATION_ERROR,
                msg=ErrorCode.VALIDATION_ERROR.description,
                errors=exc.errors(),
            )
        ),
        headers={},
    )


@app.exception_handler(RequestValidationError)
async def handle_request_validation_error(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    if any(
        error.get("type", None) == ErrorCode.JSON_INVALID.code for error in exc.errors()
    ):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(
                ErrorResponse(
                    request,
                    error_code=ErrorCode.JSON_INVALID,
                    msg=ErrorCode.JSON_INVALID.description,
                )
            ),
            headers={},
        )
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            ValidationErrorResponse(
                request,
                error_code=ErrorCode.VALIDATION_ERROR,
                msg=ErrorCode.VALIDATION_ERROR.description,
                errors=exc.errors(),
            )
        ),
        headers={},
    )


@app.exception_handler(ValueError)
async def handle_value_error(request: Request, exc: ValueError) -> JSONResponse:
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
        content=jsonable_encoder(
            ErrorResponse(request, error_code=ErrorCode.VALIDATION_ERROR, msg=str(exc))
        ),
        headers={},
    )


@app.get("/health", tags=["Health"], include_in_schema=False)
async def health_check(session: Annotated[AsyncSession, Depends(get_db)]) -> Response:
    try:
        await session.execute(text("SELECT 1"))
        return JSONResponse({"status": "ok"})
    except Exception:
        log.exception("Health check: database unreachable")
        return JSONResponse(
            {"status": "error", "detail": "database unavailable"}, status_code=503
        )


# Public API - visible in schema for external consumers
app.include_router(auth.router, tags=["Authentication"], prefix="/v1")
app.include_router(projects.router, tags=["Projects"], prefix="/v1")

# Internal - dashboard/auth flows, not useful to API token consumers
app.include_router(
    api_token.router, tags=["API Tokens"], prefix="/v1", include_in_schema=False
)
app.include_router(
    billing.plan_router, tags=["Billing Plans"], prefix="/v1", include_in_schema=False
)
app.include_router(
    organization.router, tags=["Organizations"], prefix="/v1", include_in_schema=False
)
app.include_router(user.router, tags=["Users"], prefix="/v1", include_in_schema=False)
app.include_router(
    invitation.router, tags=["Invitations"], prefix="/v1", include_in_schema=False
)
app.include_router(role.router, tags=["Roles"], prefix="/v1", include_in_schema=False)
app.include_router(
    permission.router, tags=["Permissions"], prefix="/v1", include_in_schema=False
)
app.include_router(
    billing.subscription_router,
    tags=["Billing Subscriptions"],
    prefix="/v1",
    include_in_schema=False,
)
app.include_router(
    billing.usage_router, tags=["Billing Usage"], prefix="/v1", include_in_schema=False
)
app.include_router(
    billing.webhook_router,
    tags=["Billing Webhooks"],
    prefix="/v1",
    include_in_schema=False,
)
app.include_router(
    audit_log.router, tags=["Audit Log"], prefix="/v1", include_in_schema=False
)
app.include_router(
    notification.router, tags=["Notifications"], prefix="/v1", include_in_schema=False
)
app.include_router(
    waitlist.router, tags=["Waitlists"], prefix="/v1", include_in_schema=False
)
app.include_router(
    contact.router, tags=["Contact"], prefix="/v1", include_in_schema=False
)


def custom_openapi() -> dict[str, Any]:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        summary=app.summary,
        description=app.description,
        routes=app.routes,
    )

    if not settings.auth_enabled:
        openapi_schema["components"].pop("securitySchemes", None)
        for path in openapi_schema.get("paths", {}).values():
            for method in path.values():
                method.pop("security", None)

    openapi_schema["components"]["schemas"]["ErrorResponse"] = (
        ErrorResponse.model_json_schema()
    )

    openapi_schema["components"]["schemas"]["ValidationDetail"] = (
        ValidationDetail.model_json_schema()
    )

    openapi_schema["components"]["schemas"]["ValidationErrorResponse"] = (
        ValidationErrorResponse.model_json_schema(
            ref_template="#/components/schemas/{model}"
        )
    )

    for path_item in openapi_schema["paths"].values():
        for method, operation in path_item.items():
            if "responses" not in operation:
                operation["responses"] = {}

            if "400" not in operation["responses"]:
                operation["responses"]["400"] = {
                    "description": "Bad Request",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                        }
                    },
                }

            if (
                method.lower() in ["get", "put", "delete"]
                and "404" not in operation["responses"]
            ):
                operation["responses"]["404"] = {
                    "description": "Not Found",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ErrorResponse"}
                        }
                    },
                }

            if "422" in operation["responses"]:
                operation["responses"]["422"] = {
                    "description": "Validation Error",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ValidationErrorResponse"
                            }
                        }
                    },
                }

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # ty: ignore[invalid-assignment]
