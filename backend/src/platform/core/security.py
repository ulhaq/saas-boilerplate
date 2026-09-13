from time import time
from typing import Any, Literal, Self
from uuid import uuid4

from argon2 import PasswordHasher
from fastapi.security import OAuth2PasswordBearer
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from jwt import ExpiredSignatureError, InvalidTokenError, decode, encode
from pydantic import BaseModel

from src.platform.core.config import settings
from src.platform.core.exceptions import (
    NotAuthenticatedException,
    PermissionDeniedException,
)
from src.platform.enums import ErrorCode
from src.platform.models.user import User

type TokenType = Literal["access", "refresh"]

JWT_ALGORITHM = "HS256"


class _Argon2Context:
    """argon2-cffi wrapper with passlib-style argument order (plain, hashed).

    Module-level so tests can swap in a fast hasher.
    """

    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def hash(self, secret: str) -> str:
        return self._hasher.hash(secret)

    def verify(self, plain: str, hashed: str) -> bool:
        try:
            return self._hasher.verify(hashed, plain)
        except Exception:
            return False


crypt_context = _Argon2Context()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="v1/auth/token", auto_error=False)
BEARER_HEADERS: dict[str, str] = {"WWW-Authenticate": "Bearer"}


class Auth(BaseModel):
    id: int
    name: str
    email: str
    organization_id: int
    roles: list[str]
    permissions: list[str]

    @classmethod
    def from_user_model(cls, user_model: User, active_organization_id: int) -> Self:
        organization_roles = [
            r for r in user_model.roles if r.organization_id == active_organization_id
        ]
        return cls(
            id=user_model.id,
            name=user_model.name,
            email=user_model.email,
            organization_id=active_organization_id,
            permissions=[
                permission.name
                for role in organization_roles
                for permission in role.permissions
            ],
            roles=[role.name for role in organization_roles],
        )

    def has_permission(self, permission_name: str) -> bool:
        return permission_name in self.permissions

    def authorize(self, permission: str) -> None:
        if self.has_permission(permission):
            return
        raise PermissionDeniedException


class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class JWTTokenClaims(BaseModel):
    iss: str
    sub: str
    aud: str
    exp: int
    iat: int
    jti: str
    typ: str
    roles: list[str]

    name: str | None = None
    email: str | None = None
    oid: int | None = None


type SignSalt = Literal[
    "reset-password", "email-verification", "complete-registration", "invite"
]


def sign(data: Any, salt: SignSalt) -> str:
    s = URLSafeTimedSerializer(
        secret_key=settings.app_secret.get_secret_value(), salt=salt
    )
    return s.dumps(data)


def unsign(token: str, salt: SignSalt, max_age: int = 10 * 60) -> Any:
    try:
        s = URLSafeTimedSerializer(
            secret_key=settings.app_secret.get_secret_value(), salt=salt
        )
        return s.loads(token, max_age=max_age)
    except SignatureExpired as exc:
        raise NotAuthenticatedException(
            "Signature expired", error_code=ErrorCode.SIGNATURE_EXPIRED
        ) from exc
    except BadSignature as exc:
        raise NotAuthenticatedException(
            "Signature invalid", error_code=ErrorCode.SIGNATURE_INVALID
        ) from exc


def hash_secret(secret: str) -> str:
    return crypt_context.hash(secret)


def verify_secret(plain_secret: str, hashed_secret: str) -> bool:
    try:
        return crypt_context.verify(plain_secret, hashed_secret)
    except Exception:
        return False


def decode_token(token: str, *, expected_type: TokenType = "access") -> dict:
    try:
        payload = decode(
            token,
            settings.app_secret.get_secret_value(),
            algorithms=[JWT_ALGORITHM],
            audience=settings.app_name,
            issuer=settings.app_name,
        )
    except ExpiredSignatureError as exc:
        raise NotAuthenticatedException(
            "Token expired", error_code=ErrorCode.TOKEN_EXPIRED, headers=BEARER_HEADERS
        ) from exc
    except InvalidTokenError as exc:
        raise NotAuthenticatedException(headers=BEARER_HEADERS) from exc

    # Access and refresh tokens share secret and shape; the typ claim is what
    # prevents one from being accepted where the other is expected.
    if payload.get("typ") != expected_type:
        raise NotAuthenticatedException(
            "Token invalid", error_code=ErrorCode.TOKEN_INVALID, headers=BEARER_HEADERS
        )
    return payload


def create_token(
    user: User,
    expiry: int,
    *,
    include_user_claims: bool = True,
    organization_id: int | None = None,
    jti: str | None = None,
    token_type: TokenType = "access",
) -> str:
    claims = JWTTokenClaims(
        iss=settings.app_name,
        aud=settings.app_name,
        sub=str(user.id),
        exp=int(time() + expiry),
        iat=int(time()),
        jti=jti or str(uuid4()),
        typ=token_type,
        roles=[role.name for role in user.roles],
    )
    if include_user_claims:
        claims.name = user.name
        claims.email = user.email
        claims.oid = organization_id
    return encode(
        claims.model_dump(exclude_none=True),
        settings.app_secret.get_secret_value(),
        algorithm=JWT_ALGORITHM,
    )


def authenticate_user(password: str, user: User | None) -> User | None:
    if user and verify_secret(password, user.password):
        return user
    return None
