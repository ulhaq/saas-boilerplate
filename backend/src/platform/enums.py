"""Platform enums for the generic SaaS core.

Nothing in this module may reference the product domain. Domain enums live in
the product package (e.g. `src.example.enums`) and are merged into the seeded
permission/role sets by the composition root (`src.bootstrap`).
"""

from enum import Enum, StrEnum

OWNER_ROLE_NAME = "Owner"


class ComparisonOperator(Enum):
    EQUALS = "eq"
    NOT_EQUALS = "neq"
    LESS_THAN = "lt"
    LESS_THAN_OR_EQUAL_TO = "lte"
    GREATER_THAN = "gt"
    GREATER_THAN_OR_EQUAL_TO = "gte"
    CONTAINS = "co"
    INSENSITIVE_CONTAINS = "ico"
    NOT_CONTAINS = "nco"
    INSENSITIVE_NOT_CONTAINS = "inco"
    IN = "in"
    NOT_IN = "nin"
    BETWEEN = "between"


class ErrorCodeEnum(Enum):
    """Base for error-code enums: members are (code, description) tuples.

    Domain modules define their own subclasses (e.g. `ExampleErrorCode`);
    exceptions and error responses accept any `ErrorCodeEnum` member.
    """

    code: str
    description: str

    def __init__(self, code: str, description: str):
        self.code = code
        self.description = description


class ErrorCode(ErrorCodeEnum):
    SERVER_ERROR = ("server_error", "Something went wrong on our end.")
    VALIDATION_ERROR = (
        "validation_error",
        "The request failed due to validation errors",
    )
    UNAUTHORIZED = ("unauthorized", "You are not authenticated")
    LOGIN_FAILED = ("login_failed", "Invalid email or password")
    PERMISSION_DENIED = (
        "permission_denied",
        "You are not authorized to perform this action",
    )
    JSON_INVALID = ("json_invalid", "Problems parsing JSON")
    TOKEN_EXPIRED = ("token_expired", "The authentication token has expired")
    TOKEN_INVALID = ("token_invalid", "The authentication token is invalid")
    SIGNATURE_EXPIRED = ("signature_expired", "The signature has expired")
    SIGNATURE_INVALID = ("signature_invalid", "The signature is invalid")
    PARAMETER_INVALID = (
        "parameter_invalid",
        "One or more request parameters are invalid or not allowed",
    )
    RESOURCE_NOT_FOUND = (
        "resource_not_found",
        "The requested resource could not be found",
    )
    RESOURCE_ALREADY_EXISTS = (
        "resource_already_exists",
        "The requested resource already exists",
    )
    EMAIL_ALREADY_EXISTS = ("email_already_exists", "The provided email already exists")
    ROLE_NAME_TAKEN = ("role_name_taken", "A role with this name already exists")
    ORG_NAME_TAKEN = (
        "org_name_taken",
        "An organization with this name already exists",
    )
    MULTIPLE_ORGANIZATIONS_DISABLED = (
        "multiple_organizations_disabled",
        "Creating additional organizations is disabled",
    )
    BILLING_ERROR = ("billing_error", "A billing provider error occurred")
    BILLING_WEBHOOK_INVALID = (
        "billing_webhook_invalid",
        "Webhook signature verification failed",
    )
    SUBSCRIPTION_ALREADY_ACTIVE = (
        "subscription_already_active",
        "Organization already has an active subscription",
    )
    SUBSCRIPTION_NOT_FOUND = (
        "subscription_not_found",
        "No active subscription found for this organization",
    )
    TRIAL_ALREADY_USED = (
        "trial_already_used",
        "A free trial has already been used for this organization",
    )
    PROTECTED_ROLE_MODIFICATION = (
        "protected_role_modification",
        "Protected roles cannot be modified or deleted",
    )
    OWNER_ROLE_ASSIGNMENT = (
        "owner_role_assignment",
        "The Owner role cannot be assigned or removed directly; use ownership transfer",
    )
    OWNER_REMOVAL = (
        "owner_removal",
        "The organization owner cannot be removed; transfer ownership first",
    )
    PLAN_FEATURE_UNAVAILABLE = (
        "plan_feature_unavailable",
        "Your current plan does not include this feature",
    )
    LIMIT_EXCEEDED = (
        "limit_exceeded",
        "You have reached your plan's usage limit for this period",
    )
    CAPACITY_EXCEEDED = (
        "capacity_exceeded",
        "You have reached your plan's limit for this resource",
    )


class Permission(StrEnum):
    UPDATE_ORGANIZATION = "update:organization"
    MANAGE_ORGANIZATION_USER = "manage:organization_user"
    READ_USER = "read:user"
    READ_ROLE = "read:role"
    CREATE_ROLE = "create:role"
    UPDATE_ROLE = "update:role"
    DELETE_ROLE = "delete:role"
    MANAGE_USER_ROLE = "manage:user_role"
    READ_PERMISSION = "read:permission"
    MANAGE_ROLE_PERMISSION = "manage:role_permission"
    MANAGE_SUBSCRIPTION = "manage:subscription"
    MANAGE_API_TOKEN = "manage:api_token"
    READ_AUDIT_LOG = "read:audit_log"


class AuditAction(StrEnum):
    AUTH_LOGIN = "auth.login"
    AUTH_REGISTER = "auth.register"
    AUTH_PASSWORD_RESET = "auth.password_reset"
    USER_INVITE = "user.invite"
    USER_UPDATE = "user.update"
    USER_DELETE = "user.delete"
    USER_ROLE_ASSIGN = "user.role_assign"
    USER_PASSWORD_CHANGE = "user.password_change"
    USER_PROFILE_UPDATE = "user.profile_update"
    USER_CONSENT = "user.consent"
    USER_EXPORT = "user.export"
    USER_SELF_DELETE = "user.self_delete"
    USER_ANONYMIZE = "user.anonymize"
    ROLE_CREATE = "role.create"
    ROLE_UPDATE = "role.update"
    ROLE_DELETE = "role.delete"
    ROLE_PERMISSION_ASSIGN = "role.permission_assign"
    API_TOKEN_CREATE = "api_token.create"
    API_TOKEN_DELETE = "api_token.delete"
    BILLING_WEBHOOK = "billing.webhook"
    ORG_CREATE = "org.create"
    ORG_UPDATE = "org.update"
    ORG_DELETE = "org.delete"
    ORG_OWNERSHIP_TRANSFER = "org.ownership_transfer"
    BILLING_CHECKOUT_START = "billing.checkout_start"
    BILLING_TRIAL_START = "billing.trial_start"
    BILLING_SUBSCRIPTION_CANCEL = "billing.subscription_cancel"
    BILLING_SUBSCRIPTION_RESUME = "billing.subscription_resume"
    BILLING_PLAN_SWITCH = "billing.plan_switch"
    BILLING_EMAIL_UPDATE = "billing.email_update"


# Platform-only role grants. Domain modules contribute additional per-role
# permissions (e.g. project permissions) via the composition root - seeding
# code must use `src.bootstrap.DEFAULT_ROLES`, not this list.
#
# Newly created organizations are seeded with only the protected Owner role;
# organization owners create any additional roles themselves.
DEFAULT_ROLES: list[tuple[str, str, list[StrEnum]]] = []


PERMISSION_DESCRIPTIONS: dict[StrEnum, str] = {
    Permission.UPDATE_ORGANIZATION: "Allows the user to update organization accounts.",
    Permission.MANAGE_ORGANIZATION_USER: (
        "Allows the user to manage organizations' users."
    ),
    Permission.READ_USER: "Allows the user to read users.",
    Permission.READ_ROLE: "Allows the user to read roles.",
    Permission.CREATE_ROLE: "Allows the user to create new roles.",
    Permission.UPDATE_ROLE: "Allows the user to update roles.",
    Permission.DELETE_ROLE: "Allows the user to delete roles.",
    Permission.MANAGE_USER_ROLE: "Allows the user to manage users' roles.",
    Permission.READ_PERMISSION: "Allows the user to read permissions.",
    Permission.MANAGE_ROLE_PERMISSION: "Allows the user to manage roles' permissions.",
    Permission.MANAGE_SUBSCRIPTION: "Allows managing the organization's subscription.",
    Permission.MANAGE_API_TOKEN: (
        "Allows the user to create and manage their own API tokens."
    ),
    Permission.READ_AUDIT_LOG: "Allows the user to read the organization's audit log.",
}


class PlanFeature(StrEnum):
    API_TOKEN = "api_token"


class UsageMetric(StrEnum):
    SEATS = "seats"


class RefreshTokenRevokeReason(StrEnum):
    ROTATED = "rotated"
    LOGOUT = "logout"


class Locale(StrEnum):
    DA = "da"
    EN = "en"
