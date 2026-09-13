from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Integer, String, UniqueConstraint, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.platform.core.database import Base
from src.platform.models.mixins import ResourceModel, TimestampMixin
from src.platform.models.permission import Permission, RolePermission

if TYPE_CHECKING:
    from src.platform.models.organization import Organization
    from src.platform.models.user import User


class Role(ResourceModel):
    __tablename__ = "role"

    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)
    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(
            "organization.id",
            name="fk_role_organization_id_organization",
            ondelete="CASCADE",
        ),
        nullable=False,
    )
    is_protected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="0"
    )

    organization: Mapped[Organization] = relationship(
        "Organization", back_populates="roles"
    )
    permissions: Mapped[list[Permission]] = relationship(
        Permission,
        secondary="role_permission",
        secondaryjoin=and_(
            RolePermission.permission_id == Permission.id,
            Permission.deleted_at.is_(None),
        ),
        back_populates="roles",
        lazy="joined",
        passive_deletes=True,
    )
    users: Mapped[list[User]] = relationship(
        "User", secondary="user_role", back_populates="roles", passive_deletes=True
    )


class UserRole(Base, TimestampMixin):
    __tablename__ = "user_role"
    __table_args__ = (UniqueConstraint("user_id", "role_id", name="uq_user_role"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("user.id", ondelete="CASCADE")
    )
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id", ondelete="CASCADE")
    )
