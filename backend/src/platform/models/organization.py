from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, String, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.platform.models.mixins import ResourceModel
from src.platform.models.user import User
from src.platform.models.user_organization import UserOrganization

if TYPE_CHECKING:
    from src.platform.models.role import Role


class Organization(ResourceModel):
    __tablename__ = "organization"

    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    external_customer_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, unique=True
    )
    billing_email: Mapped[str] = mapped_column(String, nullable=False)
    has_payment_method: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    trial_used: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    trial_reminder_sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None, nullable=True
    )

    users: Mapped[list[User]] = relationship(
        User,
        secondary="user_organization",
        secondaryjoin=and_(
            UserOrganization.user_id == User.id, User.deleted_at.is_(None)
        ),
        back_populates="organizations",
        lazy="selectin",
        passive_deletes=True,
    )
    roles: Mapped[list[Role]] = relationship(
        back_populates="organization", passive_deletes=True
    )
