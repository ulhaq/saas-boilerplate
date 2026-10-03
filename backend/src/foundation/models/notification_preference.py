from datetime import UTC, datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.foundation.core.database import Base


class NotificationPreference(Base):
    """A user's choice for one notification category, across organizations.
    No row means the category's defaults (`NotificationCategory`)."""

    __tablename__ = "notification_preference"

    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("user.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category: Mapped[str] = mapped_column(String(64), primary_key=True)
    in_app: Mapped[bool] = mapped_column(Boolean, nullable=False)
    email: Mapped[bool] = mapped_column(Boolean, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
