from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.platform.core.database import Base
from src.platform.models.mixins import ResourceModel, TimestampMixin

if TYPE_CHECKING:
    from src.platform.models.role import Role


class Permission(ResourceModel):
    __tablename__ = "permission"

    name: Mapped[str] = mapped_column(String, index=True, unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String, nullable=True)

    roles: Mapped[list[Role]] = relationship(
        "Role",
        secondary="role_permission",
        back_populates="permissions",
        passive_deletes=True,
    )


class RolePermission(Base, TimestampMixin):
    __tablename__ = "role_permission"
    __table_args__ = (
        UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    role_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("role.id", ondelete="CASCADE")
    )
    permission_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("permission.id", ondelete="CASCADE")
    )
