import hashlib
from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.platform.models.invitation import Invitation


def hash_invite_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class InvitationRepository:
    """Invitations are looked up by token across organizations (the invitee
    isn't a member yet), so this repository is intentionally unscoped."""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_token(self, token: str) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.token_hash == hash_invite_token(token)
        )
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def list_for_organization(self, organization_id: int) -> list[Invitation]:
        stmt = (
            select(Invitation)
            .where(Invitation.organization_id == organization_id)
            .order_by(Invitation.created_at.desc(), Invitation.id.desc())
        )
        rs = await self.db.execute(stmt)
        return list(rs.scalars().all())

    async def get_for_organization(
        self, invitation_id: int, organization_id: int
    ) -> Invitation | None:
        stmt = select(Invitation).where(
            Invitation.id == invitation_id,
            Invitation.organization_id == organization_id,
        )
        rs = await self.db.execute(stmt)
        return rs.scalar_one_or_none()

    async def replace(
        self,
        *,
        organization_id: int,
        email: str,
        role_ids: list[int],
        token: str,
        invited_by_id: int | None,
        expires_at: datetime,
    ) -> Invitation:
        """Create the invitation, replacing any pending one for the same
        organization and email (its old link stops working)."""
        await self.db.execute(
            delete(Invitation).where(
                Invitation.organization_id == organization_id,
                Invitation.email == email,
            )
        )
        record = Invitation(
            organization_id=organization_id,
            email=email,
            role_ids=role_ids,
            token_hash=hash_invite_token(token),
            invited_by_id=invited_by_id,
            expires_at=expires_at,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def delete(self, invitation: Invitation) -> None:
        await self.db.delete(invitation)
        await self.db.flush()
