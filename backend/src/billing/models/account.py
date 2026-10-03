from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.platform.models.mixins import ResourceModelBase

if TYPE_CHECKING:
    from src.platform.models.organization import Organization


class BillingAccount(ResourceModelBase):
    """An organization's billing profile: its provider customer, billing email
    and trial state. One per organization, created with the organization."""

    __tablename__ = "billing_account"

    organization_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("organization.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
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

    organization: Mapped[Organization] = relationship(lazy="selectin")
