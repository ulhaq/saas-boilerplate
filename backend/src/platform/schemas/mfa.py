from typing import Literal

from pydantic import BaseModel

from src.platform.schemas.types import NonEmptyStr


class MfaChallengeOut(BaseModel):
    """Returned instead of a Token when the password was correct but a second
    factor is required. Exchange it at POST /auth/mfa/verify."""

    mfa_required: Literal[True] = True
    mfa_token: str


class MfaVerifyIn(BaseModel):
    mfa_token: NonEmptyStr
    code: NonEmptyStr


class MfaSetupOut(BaseModel):
    secret: str
    otpauth_uri: str


class MfaCodeIn(BaseModel):
    code: NonEmptyStr


class MfaDisableIn(BaseModel):
    password: NonEmptyStr
    code: NonEmptyStr


class MfaRecoveryCodesOut(BaseModel):
    recovery_codes: list[str]
