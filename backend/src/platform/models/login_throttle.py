from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from src.platform.core.database import Base


class LoginThrottle(Base):
    """Recent failed password sign-ins per email address.

    Kept whether or not an account exists for the address, so the lockout
    behaves the same for both and reveals nothing about which addresses have
    accounts. Expired rows are purged by the GDPR retention loop.
    """

    __tablename__ = "login_throttle"

    email: Mapped[str] = mapped_column(String, primary_key=True)
    failed_attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_failed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        index=True,
    )
    locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
