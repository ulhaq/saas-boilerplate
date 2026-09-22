from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.platform.core.database import Base

if TYPE_CHECKING:
    from src.platform.models.user import User


class Invitation(Base):
    """A pending invitation to join an organization.

    One row per (organization, email): re-inviting replaces the row (and its
    link), while invites from different organizations coexist. Rows are
    deleted when accepted and purged by the GDPR worker once expired.
    """

    __tablename__ = "invitation"
    __table_args__ = (
        UniqueConstraint(
            "organization_id", "email", name="uq_invitation_organization_email"
        ),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    organization_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("organization.id", ondelete="CASCADE"), nullable=False
    )
    email: Mapped[str] = mapped_column(String, index=True, nullable=False)
    role_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    token_hash: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    invited_by_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )

    invited_by: Mapped[User | None] = relationship("User", lazy="selectin")
