from typing import Any

from fastapi import HTTPException, status

from src.platform.enums import ErrorCode, ErrorCodeEnum


class UnscopedQueryError(RuntimeError):
    """An organization-scoped repository was queried without a tenant scope.

    This is a programming error (missing set_organization_scope or .unscoped),
    never a client-facing condition - so it is deliberately not a
    ClientException and surfaces as a 500.
    """


class ClientException(HTTPException):
    error_code: ErrorCodeEnum

    def __init__(
        self,
        status_code: int,
        detail: Any = None,
        /,
        *,
        error_code: ErrorCodeEnum,
        headers: dict | None = None,
    ) -> None:
        super().__init__(status_code, detail, headers)

        self.error_code = error_code


class NotAuthenticatedException(ClientException):
    def __init__(
        self,
        detail: Any = "Not authenticated",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.UNAUTHORIZED,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_401_UNAUTHORIZED, detail, error_code=error_code, headers=headers
        )


class PermissionDeniedException(ClientException):
    def __init__(
        self,
        detail: Any = "You are not authorized to perform this action",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.PERMISSION_DENIED,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_403_FORBIDDEN, detail, error_code=error_code, headers=headers
        )


class NotFoundException(ClientException):
    def __init__(
        self,
        detail: Any = "Resource not found",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.RESOURCE_NOT_FOUND,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_404_NOT_FOUND, detail, error_code=error_code, headers=headers
        )


class AlreadyExistsException(ClientException):
    def __init__(
        self,
        detail: Any = "Resource already exists",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.RESOURCE_ALREADY_EXISTS,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_409_CONFLICT, detail, error_code=error_code, headers=headers
        )


class ValidationException(ClientException):
    def __init__(
        self,
        detail: Any = "Validation failed",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.VALIDATION_ERROR,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail,
            error_code=error_code,
            headers=headers,
        )


class BillingProviderException(ClientException):
    def __init__(
        self,
        detail: Any = "Billing provider error",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.BILLING_ERROR,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_502_BAD_GATEWAY, detail, error_code=error_code, headers=headers
        )


class PlanFeatureUnavailableException(ClientException):
    def __init__(
        self,
        detail: Any = "Your current plan does not include this feature",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.PLAN_FEATURE_UNAVAILABLE,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail,
            error_code=error_code,
            headers=headers,
        )


class BillingWebhookException(ClientException):
    def __init__(
        self,
        detail: Any = "Invalid webhook signature",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.BILLING_WEBHOOK_INVALID,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_400_BAD_REQUEST, detail, error_code=error_code, headers=headers
        )


class LimitExceededException(ClientException):
    def __init__(
        self,
        detail: Any = "You have reached your plan's usage limit for this period",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.LIMIT_EXCEEDED,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_429_TOO_MANY_REQUESTS,
            detail,
            error_code=error_code,
            headers=headers,
        )


class CapacityExceededException(ClientException):
    def __init__(
        self,
        detail: Any = "You have reached your plan's limit for this resource",
        /,
        *,
        error_code: ErrorCodeEnum = ErrorCode.CAPACITY_EXCEEDED,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_402_PAYMENT_REQUIRED,
            detail,
            error_code=error_code,
            headers=headers,
        )
