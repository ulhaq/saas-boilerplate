from collections.abc import Callable
from typing import Annotated

from fastapi import Depends

from src.platform.core.config import settings
from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotAuthenticatedException,
    NotFoundException,
    PermissionDeniedException,
)
from src.platform.core.hooks import HookEvent, emit
from src.platform.core.security import Auth, authenticate_user, hash_secret, sign
from src.platform.enums import (
    OWNER_ROLE_NAME,
    AuditAction,
    ErrorCode,
    Permission,
    UsageMetric,
)
from src.platform.models.role import Role
from src.platform.models.user import User
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.repositories.user import UserRepository
from src.platform.schemas.common import PageQueryParams, PaginatedResponse
from src.platform.schemas.user import (
    ChangePasswordIn,
    DeleteMeIn,
    InviteUserIn,
    UserDataExportOut,
    UserOut,
    UserPatch,
    UserRoleIn,
)
from src.platform.services.base import ResourceService
from src.platform.services.mailer import send_email


class UserService(
    ResourceService[UserRepository, User, UserPatch | ChangePasswordIn, UserOut]
):
    current_user: Auth

    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ):
        self.repo = repos.user
        self.repo.set_organization_scope(current_user.organization_id)
        self.current_user = current_user
        super().__init__(repos)

    def _user_out(self, user: User) -> UserOut:
        organization_roles = [
            r
            for r in user.roles
            if r.organization_id == self.current_user.organization_id
        ]
        return UserOut.model_validate(
            {
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "locale": user.locale,
                "theme": user.theme,
                "created_at": user.created_at,
                "updated_at": user.updated_at,
                "roles": organization_roles,
            }
        )

    async def _assert_not_last_admin(self, user: User) -> None:
        organization_roles = [
            r
            for r in user.roles
            if r.organization_id == self.current_user.organization_id
        ]
        user_permissions = {
            p.name for role in organization_roles for p in role.permissions
        }
        if Permission.MANAGE_USER_ROLE.value not in user_permissions:
            return
        if not await self.repo.has_other_user_with_permission(
            Permission.MANAGE_USER_ROLE.value, exclude_user_id=user.id
        ):
            raise PermissionDeniedException(
                "Cannot perform this action: organization must retain at least one "
                "user with role management access"
            )

    async def paginate(
        self,
        schema_out: type[UserOut],
        page_query_params: PageQueryParams,
        include_deleted: bool = False,
    ) -> PaginatedResponse[UserOut]:
        items, total = await self.repo.paginate(
            sort=page_query_params.sort,
            filters=page_query_params.filters,
            page_size=page_query_params.page_size,
            page_number=page_query_params.page_number,
            include_deleted=include_deleted,
            search=page_query_params.search,
        )
        return PaginatedResponse(
            items=[self._user_out(item) for item in items],
            page_number=page_query_params.page_number,
            page_size=page_query_params.page_size,
            total=total,
        )

    async def get_authenticated_user(self) -> UserOut:
        return self._user_out(await self.get(self.current_user.id))

    async def patch_profile(self, schema_in: UserPatch) -> UserOut:
        async def validate() -> None:
            if schema_in.email:
                user = await self.repo.get_by_email(schema_in.email)
                if user and user.email != self.current_user.email:
                    raise AlreadyExistsException(
                        f"User already exists. [email={schema_in.email}]",
                        error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    )

        user = await super().patch(self.current_user.id, schema_in, validate)

        await self.log_audit(
            AuditAction.USER_PROFILE_UPDATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="user",
            resource_id=self.current_user.id,
            details={"fields": list(schema_in.model_dump(exclude_unset=True).keys())},
        )
        return self._user_out(user)

    async def change_password(self, schema_in: ChangePasswordIn) -> UserOut:
        auth = self.current_user

        user = authenticate_user(
            schema_in.password, await self.repos.user.get_by_email(auth.email)
        )

        if not user:
            raise NotAuthenticatedException(
                "Incorrect password", error_code=ErrorCode.LOGIN_FAILED
            )

        hashed_pw = hash_secret(schema_in.new_password)
        updated = await self.repo.update(user, password=hashed_pw)
        await self.log_audit(
            AuditAction.USER_PASSWORD_CHANGE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="user",
            resource_id=self.current_user.id,
        )
        return self._user_out(updated)

    async def patch_user(self, identifier: int, schema_in: UserPatch) -> UserOut:
        user = await self.get(identifier)

        async def validate() -> None:
            if schema_in.email:
                existing = await self.repo.get_by_email(schema_in.email)
                if existing and existing.email != user.email:
                    raise AlreadyExistsException(
                        f"User already exists. [email={schema_in.email}]",
                        error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
                    )

        updated = await super().patch(identifier, schema_in, validate)

        await self.log_audit(
            AuditAction.USER_UPDATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="user",
            resource_id=identifier,
        )

        return self._user_out(updated)

    async def get_user(self, identifier: int, include_deleted: bool = False) -> UserOut:
        return self._user_out(
            await super().get(identifier, include_deleted=include_deleted)
        )

    async def invite_user(
        self, invite_in: InviteUserIn, schedule_task: Callable
    ) -> None:
        count = await self.repos.user.count_for_org(self.current_user.organization_id)
        await self._require_capacity(
            UsageMetric.SEATS, self.current_user.organization_id, count
        )

        if invite_in.role_ids:
            self.repos.role.set_organization_scope(self.current_user.organization_id)
            roles = list(await self.repos.role.filter_by_ids(invite_in.role_ids))
            if any(r.is_protected and r.name == OWNER_ROLE_NAME for r in roles):
                raise PermissionDeniedException(
                    "The Owner role cannot be assigned via invitation.",
                    error_code=ErrorCode.OWNER_ROLE_ASSIGNMENT,
                )

        existing = await self.repo.get_by_email(invite_in.email)
        if existing:
            membership = (
                await self.repos.user_organization.get_by_user_and_organization(
                    user_id=existing.id,
                    organization_id=self.current_user.organization_id,
                )
            )
            if membership:
                raise AlreadyExistsException(
                    "User already exists in this organization."
                    f" [email={invite_in.email}]",
                    error_code=ErrorCode.EMAIL_ALREADY_EXISTS,
                )

        token = sign(
            data={
                "email": invite_in.email,
                "organization_id": self.current_user.organization_id,
                "role_ids": invite_in.role_ids,
            },
            salt="invite",
        )

        await self.repos.invite_token.delete_by_email(invite_in.email)
        await self.repos.invite_token.create(
            email=invite_in.email, token=hash_secret(token)
        )

        await self.log_audit(
            AuditAction.USER_INVITE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="user",
            details={"email": invite_in.email},
        )

        organization = await self.repos.organization.get(
            self.current_user.organization_id
        )
        if not organization:
            raise NotFoundException("Organization not found.")

        # Invitee has no account yet, so no stored locale; defaults to English.
        schedule_task(
            send_email,
            address=invite_in.email,
            user_name=invite_in.email,
            email_template="invite-user",
            data={
                "invite_url": f"{settings.frontend_url}/invite?token={token}",
                "organization_name": organization.name,
                "expiration_days": settings.invite_expiry // (60 * 60 * 24),
            },
        )

    async def remove_user(self, identifier: int) -> None:
        org_id = self.current_user.organization_id
        user = await self.get(identifier)

        organization_roles = [r for r in user.roles if r.organization_id == org_id]
        if any(
            r.is_protected and r.name == OWNER_ROLE_NAME for r in organization_roles
        ):
            raise PermissionDeniedException(
                "The organization owner cannot be removed. Transfer ownership first.",
                error_code=ErrorCode.OWNER_REMOVAL,
            )

        await self._assert_not_last_admin(user)

        membership = await self.repos.user_organization.get_by_user_and_organization(
            identifier, org_id
        )
        if membership:
            active = (
                await self.repos.user_organization.get_active_organization_for_user(
                    identifier
                )
            )
            if active and active.organization_id == org_id:
                await self.repos.refresh_token.delete_by_user(user)
            await self.repos.api_token.revoke_all_for_user_org(identifier, org_id)
            await emit(
                HookEvent.MEMBER_REMOVED,
                repos=self.repos,
                organization_id=org_id,
                user_id=identifier,
            )
            await self.repos.user_organization.force_delete(membership)

        remaining = await self.repos.user_organization.get_all_for_user(identifier)
        if not remaining:
            await self.repo.delete(user)

        await self.log_audit(
            AuditAction.USER_DELETE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="user",
            resource_id=identifier,
        )

    async def manage_roles(self, identifier: int, schema_in: UserRoleIn) -> UserOut:
        if self.current_user.id == identifier:
            raise PermissionDeniedException(
                "You are not allowed to manage your own roles"
            )

        user = await self.get(identifier)
        new_roles: list[Role] = []

        if schema_in.role_ids:
            self.repos.role.set_organization_scope(self.current_user.organization_id)
            new_roles = list(await self.repos.role.filter_by_ids(schema_in.role_ids))
            if len(new_roles) != len(schema_in.role_ids):
                raise PermissionDeniedException(
                    "One or more roles do not belong to your organization"
                )

        manage_permission = Permission.MANAGE_USER_ROLE.value
        organization_user_roles = [
            r
            for r in user.roles
            if r.organization_id == self.current_user.organization_id
        ]
        user_has_manage_permission = any(
            manage_permission in {p.name for p in role.permissions}
            for role in organization_user_roles
        )
        new_roles_have_manage_permission = any(
            manage_permission in {p.name for p in role.permissions}
            for role in new_roles
        )
        if user_has_manage_permission and not new_roles_have_manage_permission:
            await self._assert_not_last_admin(user)

        owner_role_in_current = any(
            r.is_protected and r.name == OWNER_ROLE_NAME
            for r in organization_user_roles
        )
        owner_role_in_new = any(
            r.is_protected and r.name == OWNER_ROLE_NAME for r in new_roles
        )
        if owner_role_in_current != owner_role_in_new:
            raise PermissionDeniedException(
                "The Owner role cannot be assigned or removed."
                " Use ownership transfer instead.",
                error_code=ErrorCode.OWNER_ROLE_ASSIGNMENT,
            )

        current_roles = {role.id for role in organization_user_roles}
        schema_in_role_ids = set(schema_in.role_ids)

        if roles_to_add := schema_in_role_ids - current_roles:
            await self.repo.add_roles(user, *roles_to_add)

        if roles_to_remove := current_roles - schema_in_role_ids:
            await self.repo.remove_roles(user, *roles_to_remove)

        if roles_to_add or roles_to_remove:
            await self.log_audit(
                AuditAction.USER_ROLE_ASSIGN,
                organization_id=self.current_user.organization_id,
                user_id=self.current_user.id,
                resource_type="user",
                resource_id=identifier,
                details={
                    "added": list(roles_to_add),
                    "removed": list(roles_to_remove),
                },
            )

        return self._user_out(user)

    async def export_me(self) -> UserDataExportOut:
        user = await self.get(self.current_user.id)
        await self.log_audit(
            AuditAction.USER_EXPORT,
            organization_id=self.current_user.organization_id,
            user_id=user.id,
        )

        memberships = await self.repos.user_organization.get_all_for_user(user.id)
        api_tokens = await self.repos.api_token.list_all_for_user(user.id)
        audit_logs = await self.repos.audit_log.get_all_for_user(user.id)

        return UserDataExportOut(
            user={
                "id": user.id,
                "name": user.name,
                "email": user.email,
                "terms_accepted_at": (
                    user.terms_accepted_at.isoformat()
                    if user.terms_accepted_at
                    else None
                ),
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            },
            organizations=[
                {
                    "organization_id": m.organization_id,
                    "last_active_at": m.last_active_at.isoformat()
                    if m.last_active_at
                    else None,
                }
                for m in memberships
            ],
            api_tokens=[
                {
                    "id": t.id,
                    "name": t.name,
                    "organization_id": t.organization_id,
                    "last_used_at": t.last_used_at.isoformat()
                    if t.last_used_at
                    else None,
                    "created_at": t.created_at.isoformat(),
                }
                for t in api_tokens
            ],
            audit_logs=[
                {
                    "action": log.action,
                    "organization_id": log.organization_id,
                    "resource_type": log.resource_type,
                    "resource_id": log.resource_id,
                    "ip_address": log.ip_address,
                    "created_at": log.created_at.isoformat(),
                }
                for log in audit_logs
            ],
        )

    async def delete_me(self, schema_in: DeleteMeIn, schedule_task: Callable) -> None:
        user = authenticate_user(
            schema_in.current_password,
            await self.repos.user.get_by_email(self.current_user.email),
        )
        if not user:
            raise NotAuthenticatedException(
                "Incorrect password", error_code=ErrorCode.LOGIN_FAILED
            )

        owner_orgs = [
            r.organization_id
            for r in user.roles
            if r.is_protected and r.name == OWNER_ROLE_NAME
        ]
        if owner_orgs:
            raise PermissionDeniedException(
                "You are the owner of one or more organizations. "
                "Transfer ownership before deleting your account.",
                error_code=ErrorCode.OWNER_REMOVAL,
            )

        memberships = await self.repos.user_organization.get_all_for_user(user.id)

        roles_by_org: dict[int, list[int]] = {}
        for role in user.roles:
            roles_by_org.setdefault(role.organization_id, []).append(role.id)

        membership_snapshot = [
            {
                "organization_id": m.organization_id,
                "role_ids": roles_by_org.get(m.organization_id, []),
            }
            for m in memberships
        ]

        for membership in memberships:
            await self.repos.api_token.revoke_all_for_user_org(
                user.id, membership.organization_id
            )
            await emit(
                HookEvent.MEMBER_REMOVED,
                repos=self.repos,
                organization_id=membership.organization_id,
                user_id=user.id,
            )
            await self.repos.user_organization.force_delete(membership)

        await self.repos.refresh_token.delete_by_user(user)
        await self.repo.delete(user)

        await self.log_audit(
            AuditAction.USER_SELF_DELETE,
            organization_id=self.current_user.organization_id,
            user_id=user.id,
            details={"memberships": membership_snapshot},
        )

        schedule_task(
            send_email,
            address=user.email,
            user_name=user.name,
            email_template="account-deletion",
            locale=user.locale,
            data={
                "retention_days": settings.gdpr_retention_days,
            },
        )
