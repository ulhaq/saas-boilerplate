from typing import TYPE_CHECKING

from sqlalchemy import String, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.foundation.models.mixins import ResourceModel
from src.foundation.models.user import User
from src.foundation.models.user_organization import UserOrganization

if TYPE_CHECKING:
    from src.foundation.models.role import Role


class Organization(ResourceModel):
    __tablename__ = "organization"

    name: Mapped[str] = mapped_column(String, index=True, nullable=False)

    users: Mapped[list[User]] = relationship(
        User,
        secondary="user_organization",
        secondaryjoin=and_(
            UserOrganization.user_id == User.id,
            User.deleted_at.is_(None),
        ),
        back_populates="organizations",
        lazy="selectin",
        passive_deletes=True,
    )
    roles: Mapped[list[Role]] = relationship(
        back_populates="organization",
        passive_deletes=True,
    )
