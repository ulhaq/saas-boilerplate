import hashlib
import secrets
from typing import Annotated

from fastapi import Depends

from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import NotFoundException, ValidationException
from src.platform.core.security import Auth
from src.platform.enums import AuditAction, ErrorCode
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.api_token import (
    ApiTokenCreate,
    ApiTokenCreatedResponse,
    ApiTokenResponse,
)
from src.platform.services.base import BaseService


class ApiTokenService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.current_user = current_user
        super().__init__(repos)

    async def create_token(self, schema_in: ApiTokenCreate) -> ApiTokenCreatedResponse:
        user_permissions = set(self.current_user.permissions)
        invalid = set(schema_in.permissions) - user_permissions
        if invalid:
            raise ValidationException(ErrorCode.PARAMETER_INVALID)

        plaintext = "sk_" + secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(plaintext.encode()).hexdigest()
        _prefix_start = len("sk_")
        _prefix_len = 8
        token_prefix = plaintext[_prefix_start : _prefix_start + _prefix_len]

        token = await self.repos.api_token.create(
            user_id=self.current_user.id,
            organization_id=self.current_user.organization_id,
            name=schema_in.name,
            token_hash=token_hash,
            token_prefix=token_prefix,
            permissions=list(schema_in.permissions),
            expires_at=schema_in.expires_at,
        )
        await self.log_audit(
            AuditAction.API_TOKEN_CREATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="api_token",
            resource_id=token.id,
            details={"name": schema_in.name},
        )
        data = ApiTokenResponse.model_validate(token)
        return ApiTokenCreatedResponse(**data.model_dump(), token=plaintext)

    async def list_tokens(self) -> list[ApiTokenResponse]:
        tokens = await self.repos.api_token.list_for_user_org(
            self.current_user.id, self.current_user.organization_id
        )
        return [ApiTokenResponse.model_validate(t) for t in tokens]

    async def revoke_token(self, token_id: int) -> None:
        revoked = await self.repos.api_token.revoke(
            token_id, self.current_user.id, self.current_user.organization_id
        )
        if not revoked:
            raise NotFoundException("API token not found")
        await self.log_audit(
            AuditAction.API_TOKEN_DELETE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="api_token",
            resource_id=token_id,
        )
