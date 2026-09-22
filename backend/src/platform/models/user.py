from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import JSON, DateTime, Integer, String, and_
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.platform.models.mixins import ResourceModel
from src.platform.models.role import Role, UserRole

if TYPE_CHECKING:
    from src.platform.models.api_token import ApiToken
    from src.platform.models.organization import Organization
    from src.platform.models.password_reset_token import PasswordResetToken
    from src.platform.models.refresh_token import RefreshToken


class User(ResourceModel):
    __tablename__ = "user"

    name: Mapped[str] = mapped_column(String, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    locale: Mapped[str] = mapped_column(String(8), nullable=False, server_default="da")
    theme: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="system"
    )
    terms_accepted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    mfa_secret: Mapped[str | None] = mapped_column(String, nullable=True)
    mfa_enabled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )
    mfa_recovery_codes: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    mfa_last_used_step: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mfa_failed_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    mfa_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

    organizations: Mapped[list[Organization]] = relationship(
        "Organization",
        secondary="user_organization",
        back_populates="users",
        lazy="selectin",
        passive_deletes=True,
    )
    roles: Mapped[list[Role]] = relationship(
        Role,
        secondary="user_role",
        secondaryjoin=and_(UserRole.role_id == Role.id, Role.deleted_at.is_(None)),
        back_populates="users",
        lazy="joined",
        passive_deletes=True,
    )
    password_reset_token: Mapped[PasswordResetToken] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    api_tokens: Mapped[list[ApiToken]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )

    @property
    def mfa_active(self) -> bool:
        return self.mfa_enabled_at is not None
