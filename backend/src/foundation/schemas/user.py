from datetime import datetime
from typing import Annotated, Any, Self

from pydantic import (
    AfterValidator,
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

from src.foundation.core.exceptions import ValidationException
from src.foundation.core.schema import ResponseSchema
from src.foundation.enums import Locale
from src.foundation.schemas.common import Timestamp
from src.foundation.schemas.role import RoleOut
from src.foundation.schemas.types import ConstrainedEmail, NonEmptyStr, Password
from src.foundation.schemas.utils import sort_by_id


class UserBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: NonEmptyStr
    email: ConstrainedEmail


class UserOut(UserBase, Timestamp, ResponseSchema):
    id: int
    locale: str = "da"
    theme: str = "system"
    terms_accepted_at: datetime | None = None
    mfa_enabled: bool = False
    roles: Annotated[list[RoleOut], AfterValidator(sort_by_id)] = Field(
        default_factory=list,
    )


class UserPatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: NonEmptyStr | None = None
    locale: Locale | None = None
    theme: str | None = None


class EmailChangeIn(BaseModel):
    new_email: ConstrainedEmail
    password: NonEmptyStr
    code: str | None = None


class ConfirmEmailChangeIn(BaseModel):
    token: NonEmptyStr


class EmailIn(BaseModel):
    email: ConstrainedEmail


class RegisterIn(BaseModel):
    email: ConstrainedEmail
    terms_accepted: bool
    locale: Locale = Locale.DA

    @field_validator("terms_accepted")
    @classmethod
    def must_accept_terms(cls, v: bool) -> bool:  # noqa: FBT001
        if not v:
            raise ValueError("You must accept the terms to continue")
        return v


class SwitchOrganizationIn(BaseModel):
    organization_id: int


class ResetPasswordIn(BaseModel):
    token: str
    password: Password


class ChangePasswordIn(BaseModel):
    password: NonEmptyStr
    new_password: Password
    confirm_password: str

    @model_validator(mode="after")
    def check_passwords_match(self) -> Self:
        if self.new_password != self.confirm_password:
            raise ValidationException("Passwords do not match")
        return self


class UserRoleIn(BaseModel):
    role_ids: list[int] = Field(default_factory=list)


class RegisterOut(BaseModel):
    message: str


class VerifyEmailIn(BaseModel):
    token: str


class SetupTokenOut(BaseModel):
    setup_token: str


class CompleteRegistrationIn(BaseModel):
    setup_token: str
    name: NonEmptyStr
    password: Password


class InviteUserIn(BaseModel):
    email: ConstrainedEmail
    role_ids: list[int] = Field(min_length=1)


class CompleteInviteIn(BaseModel):
    invite_token: str
    name: NonEmptyStr | None = None
    password: Password | None = None
    terms_accepted: bool | None = None

    @field_validator("terms_accepted")
    @classmethod
    def must_accept_terms(cls, v: bool | None) -> bool | None:  # noqa: FBT001
        if v is False:
            raise ValueError("You must accept the terms to continue")
        return v


class DeleteMeIn(BaseModel):
    current_password: NonEmptyStr


class UserDataExportOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    user: dict[str, Any]
    organizations: list[dict[str, Any]]
    api_tokens: list[dict[str, Any]]
    audit_logs: list[dict[str, Any]]
    notifications: list[dict[str, Any]]
    # What each installed module holds about the user, by module name.
    modules: dict[str, dict[str, Any]]


class AcceptInviteIn(BaseModel):
    invite_token: str


class InviteStatusIn(BaseModel):
    token: str


class InviteStatusOut(BaseModel):
    email: str
    user_exists: bool
