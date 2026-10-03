from typing import Annotated

from fastapi import APIRouter, Depends, Path, status

from src.foundation.core.security import Auth
from src.foundation.enums import Permission
from src.foundation.schemas.invitation import InvitationOut
from src.foundation.services.access import require_permission
from src.foundation.services.invitation import InvitationService

router = APIRouter(prefix="/invitations")


@router.get("", status_code=status.HTTP_200_OK)
async def list_invitations(
    service: Annotated[InvitationService, Depends()],
    _: Annotated[
        Auth,
        Depends(require_permission(Permission.MANAGE_ORGANIZATION_USER)),
    ],
) -> list[InvitationOut]:
    return await service.list_invitations()


@router.delete("/{invitation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invitation(
    service: Annotated[InvitationService, Depends()],
    _: Annotated[
        Auth,
        Depends(require_permission(Permission.MANAGE_ORGANIZATION_USER)),
    ],
    invitation_id: Annotated[int, Path()],
) -> None:
    """Deletes the invitation; its link stops working immediately."""
    await service.revoke_invitation(invitation_id)
