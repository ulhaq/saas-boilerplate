from typing import Annotated

from fastapi import Depends

from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import NotFoundException
from src.platform.core.security import Auth
from src.platform.enums import AuditAction
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.invitation import InvitationOut, InvitationRoleOut
from src.platform.services.base import BaseService


class InvitationService(BaseService):
    """Pending invitations of the current user's active organization.

    Creating invites lives in UserService.invite_user; accepting them in
    AuthService.
    """

    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.current_user = current_user
        super().__init__(repos)

    async def list_invitations(self) -> list[InvitationOut]:
        """Pending and expired-but-not-yet-purged invites (see is_expired),
        newest first, so admins can re-send or revoke either."""
        organization_id = self.current_user.organization_id
        invitations = await self.repos.invitation.list_for_organization(organization_id)

        role_ids = {rid for i in invitations for rid in i.role_ids}
        roles_by_id: dict[int, InvitationRoleOut] = {}
        if role_ids:
            self.repos.role.set_organization_scope(organization_id)
            roles_by_id = {
                r.id: InvitationRoleOut.model_validate(r)
                for r in await self.repos.role.filter_by_ids(list(role_ids))
            }

        return [
            InvitationOut.model_validate(i).model_copy(
                update={
                    "roles": [roles_by_id[r] for r in i.role_ids if r in roles_by_id]
                }
            )
            for i in invitations
        ]

    async def revoke_invitation(self, invitation_id: int) -> None:
        invitation = await self.repos.invitation.get_for_organization(
            invitation_id, self.current_user.organization_id
        )
        if not invitation:
            raise NotFoundException("Invitation not found")

        email = invitation.email
        await self.repos.invitation.delete(invitation)
        await self.log_audit(
            AuditAction.USER_INVITE_REVOKE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="invitation",
            resource_id=invitation_id,
            details={"email": email},
        )
