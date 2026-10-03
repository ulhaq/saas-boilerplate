from typing import Any

from fastapi import status

from src.billing.enums import BillingErrorCode
from src.platform.core.exceptions import ClientException
from src.platform.enums import ErrorCodeEnum


class BillingProviderException(ClientException):
    def __init__(
        self,
        detail: Any = "Billing provider error",
        /,
        *,
        error_code: ErrorCodeEnum = BillingErrorCode.BILLING_ERROR,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_502_BAD_GATEWAY,
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
        error_code: ErrorCodeEnum = BillingErrorCode.BILLING_WEBHOOK_INVALID,
        headers: dict | None = None,
    ) -> None:
        super().__init__(
            status.HTTP_400_BAD_REQUEST,
            detail,
            error_code=error_code,
            headers=headers,
        )
