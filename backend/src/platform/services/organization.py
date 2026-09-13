import logging
from datetime import UTC, datetime
from typing import Annotated

from fastapi import Depends

from src.platform.billing.dependencies import BillingProviderDep
from src.platform.core.composition import DEFAULT_ROLES
from src.platform.core.config import settings
from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import (
    AlreadyExistsException,
    NotFoundException,
    PermissionDeniedException,
)
from src.platform.core.hooks import HookEvent, emit
from src.platform.core.security import Auth
from src.platform.enums import OWNER_ROLE_NAME, AuditAction, ErrorCode
from src.platform.models.organization import Organization
from src.platform.models.user import User
from src.platform.repositories.organization import OrganizationRepository
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.common import PageQueryParams, PaginatedResponse
from src.platform.schemas.organization import (
    MyOrganizationOut,
    OrganizationBase,
    OrganizationOut,
    OrganizationPatch,
    TransferOwnershipIn,
)
from src.platform.schemas.user import UserOut
from src.platform.services.base import ResourceService

log = logging.getLogger(__name__)


async def setup_new_organization(
    repos: RepositoryManager,
    organization: Organization,
    user: User,
) -> None:
    permissions = await repos.permission.get_all()
    permission_map = {p.name: p.id for p in permissions}

    owner_role = await repos.role.create(
        name=OWNER_ROLE_NAME,
        description="Full access to all system features and settings.",
        is_protected=True,
        organization=organization,
    )
    await repos.role.add_permissions(owner_role, *permission_map.values())
    await repos.user.add_roles(user, owner_role.id)

    for role_name, role_description, role_permissions in DEFAULT_ROLES:
        role = await repos.role.create(
            name=role_name,
            description=role_description,
            is_protected=False,
            organization=organization,
        )
        await repos.role.add_permissions(
            role, *[permission_map[p] for p in role_permissions if p in permission_map]
        )

    # Create a local active free subscription. No Stripe customer or subscription
    # is created here - the free plan is local-only. A Stripe customer is created
    # when the user starts a trial or paid checkout.
    free_price = await repos.plan_price.get_free_price()
    if free_price:
        await repos.subscription.create(
            organization_id=organization.id,
            plan_price_id=free_price.id,
            status="active",
        )
    else:
        log.warning(
            "No free plan found - skipping auto-subscription for organization %s",
            organization.id,
        )


class OrganizationService(
    ResourceService[
        OrganizationRepository,
        Organization,
        OrganizationBase | OrganizationPatch,
        OrganizationOut,
    ]
):
    current_user: Auth

    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
        provider: BillingProviderDep,
    ) -> None:
        self.repo = repos.organization
        self.current_user = current_user
        self.provider = provider
        super().__init__(repos)

    async def get(self, identifier: int, include_deleted: bool = False) -> Organization:
        membership = await self.repos.user_organization.get_by_user_and_organization(
            self.current_user.id, identifier
        )
        if not membership:
            raise PermissionDeniedException(
                "You are not allowed to access other organizations"
            )
        return await super().get(identifier, include_deleted=include_deleted)

    async def paginate(
        self,
        schema_out: type[OrganizationOut],
        page_query_params: PageQueryParams,
        include_deleted: bool = False,
    ) -> PaginatedResponse[OrganizationOut]:
        return await super().paginate(
            schema_out=schema_out,
            page_query_params=page_query_params,
            include_deleted=include_deleted,
        )

    async def get_all_organizations(self) -> list[MyOrganizationOut]:
        memberships = await self.repos.user_organization.get_all_for_user(
            self.current_user.id
        )
        organization_ids = [m.organization_id for m in memberships]
        organizations = await self.repos.organization.filter_by_ids(organization_ids)
        organization_map = {o.id: o for o in organizations}
        user = await self.repos.user.unscoped.get(self.current_user.id)
        owner_org_ids = {
            r.organization_id
            for r in (user.roles if user else [])
            if r.is_protected and r.name == OWNER_ROLE_NAME
        }
        return [
            MyOrganizationOut(
                **OrganizationOut.model_validate(organization_map[oid]).model_dump(),
                is_owner=oid in owner_org_ids,
            )
            for oid in organization_ids
            if oid in organization_map
        ]

    async def create_organization(self, schema_in: OrganizationBase) -> OrganizationOut:
        if not settings.allow_multiple_organizations:
            raise PermissionDeniedException(
                "Creating additional organizations is disabled",
                error_code=ErrorCode.MULTIPLE_ORGANIZATIONS_DISABLED,
            )

        existing = await self.repo.get_by_name(schema_in.name, include_deleted=True)
        if existing is not None and existing.deleted_at is None:
            raise AlreadyExistsException(
                f"Organization already exists. [name={schema_in.name}]",
                error_code=ErrorCode.ORG_NAME_TAKEN,
            )

        if existing is not None and existing.deleted_at is not None:
            organization = await self.repo.restore(existing)
        else:
            organization = await self.repo.create(
                name=schema_in.name, billing_email=self.current_user.email
            )

        await self.repos.user_organization.create(
            user_id=self.current_user.id,
            organization_id=organization.id,
            last_active_at=datetime.now(UTC),
        )
        await emit(
            HookEvent.MEMBER_ADDED,
            repos=self.repos,
            organization_id=organization.id,
            user_id=self.current_user.id,
        )

        user = await self.repos.user.unscoped.get_one(self.current_user.id)
        await setup_new_organization(self.repos, organization, user)

        await self.log_audit(
            AuditAction.ORG_CREATE,
            organization_id=organization.id,
            user_id=self.current_user.id,
            resource_type="organization",
            resource_id=organization.id,
            details={"name": organization.name},
        )
        return OrganizationOut.model_validate(organization)

    async def patch_organization(
        self, identifier: int, schema_in: OrganizationPatch
    ) -> OrganizationOut:
        if identifier != self.current_user.organization_id:
            raise PermissionDeniedException(
                "You can only update your active organization"
            )

        async def validate() -> None:
            if schema_in.name:
                existing_org = await self.repo.get_by_name(schema_in.name)
                if existing_org and existing_org.id != identifier:
                    raise AlreadyExistsException(
                        f"Organization already exists. [name={schema_in.name}]"
                    )

        updated = await super().patch(identifier, schema_in, validate)
        await self.log_audit(
            AuditAction.ORG_UPDATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="organization",
            resource_id=identifier,
        )

        return OrganizationOut.model_validate(updated)

    async def get_organization(self, identifier: int) -> OrganizationOut:
        return OrganizationOut.model_validate(await self.get(identifier))

    async def delete_organization(
        self, identifier: int, force_delete: bool = False
    ) -> None:
        if identifier != self.current_user.organization_id:
            raise PermissionDeniedException(
                "You can only delete your active organization"
            )

        subscription = await self.repos.subscription.get_active_for_organization(
            identifier
        )
        if subscription and subscription.external_subscription_id:
            raise PermissionDeniedException(
                "Cannot delete an organization with an active subscription."
                " Cancel the subscription first.",
                error_code=ErrorCode.SUBSCRIPTION_ALREADY_ACTIVE,
            )

        # Load members before deletion so the DB cascade hasn't removed the rows yet
        memberships = (
            await self.repos.user_organization.get_all_members_of_organization(
                identifier
            )
        )
        for membership in memberships:
            user = await self.repos.user.unscoped.get(membership.user_id)
            if not user:
                continue
            # get_all_for_user filters soft-deleted orgs
            # so this gives remaining active orgs
            other = await self.repos.user_organization.get_all_for_user(
                membership.user_id
            )
            if not any(m.organization_id != identifier for m in other):
                await self.repos.refresh_token.delete_by_user(user)
                await self.repos.user.delete(user)

        await self.log_audit(
            AuditAction.ORG_DELETE,
            organization_id=identifier,
            user_id=self.current_user.id,
            resource_type="organization",
            resource_id=identifier,
        )
        await super().delete(identifier, force_delete=force_delete)

    async def get_organization_users(
        self, organization_id: int, page_query_params: PageQueryParams
    ) -> PaginatedResponse[UserOut]:
        await self.get(organization_id)  # validates access

        self.repos.user.set_organization_scope(organization_id)
        items, total = await self.repos.user.paginate(
            sort=page_query_params.sort,
            filters=page_query_params.filters,
            page_size=page_query_params.page_size,
            page_number=page_query_params.page_number,
        )
        result = [
            UserOut.model_validate(
                {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "created_at": user.created_at,
                    "updated_at": user.updated_at,
                    "roles": [
                        role
                        for role in user.roles
                        if role.organization_id == organization_id
                    ],
                }
            )
            for user in items
        ]
        return PaginatedResponse(
            items=result,
            page_number=page_query_params.page_number,
            page_size=page_query_params.page_size,
            total=total,
        )

    async def transfer_ownership(
        self, organization_id: int, schema_in: TransferOwnershipIn
    ) -> None:
        if organization_id != self.current_user.organization_id:
            raise PermissionDeniedException(
                "You can only transfer ownership of your active organization"
            )

        if schema_in.user_id == self.current_user.id:
            raise PermissionDeniedException("Cannot transfer ownership to yourself")

        organization = await self.get(organization_id)

        membership = await self.repos.user_organization.get_by_user_and_organization(
            schema_in.user_id, organization_id
        )
        if not membership:
            raise NotFoundException("Target user is not a member of this organization")

        self.repos.role.set_organization_scope(organization_id)
        owner_role = await self.repos.role.get_by_name(OWNER_ROLE_NAME)
        if not owner_role:
            raise NotFoundException("Owner role not found")

        current_owner = await self.repos.user.unscoped.get_one(self.current_user.id)
        new_owner = await self.repos.user.unscoped.get_one(schema_in.user_id)

        await self.repos.user.remove_roles(current_owner, owner_role.id)
        await self.repos.user.add_roles(new_owner, owner_role.id)

        await self.log_audit(
            AuditAction.ORG_OWNERSHIP_TRANSFER,
            organization_id=organization_id,
            user_id=self.current_user.id,
            resource_type="organization",
            resource_id=organization_id,
            details={
                "from_user_id": self.current_user.id,
                "to_user_id": schema_in.user_id,
            },
        )

        if organization.external_customer_id:
            await self.provider.update_customer(
                organization.external_customer_id, email=new_owner.email
            )
