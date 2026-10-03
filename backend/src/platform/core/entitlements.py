"""What an organization may use: features and per-metric limits.

The platform asks these questions (an API-token feature, a seat limit, a
product's project limit) without knowing what answers them. A module that sells
plans - `src.billing` - provides an `Entitlements` in its manifest; without one,
every organization gets every feature with no limits (`UNLIMITED`).
"""

from typing import Protocol

from sqlalchemy.ext.asyncio import AsyncSession


class Entitlements(Protocol):
    async def has_feature(
        self, db: AsyncSession, organization_id: int, feature: str
    ) -> bool: ...

    async def limit(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> int | None:
        """The organization's cap for ``metric``; ``None`` means unlimited."""
        ...

    async def usage(self, db: AsyncSession, organization_id: int, metric: str) -> int:
        """How much of a per-period ``metric`` was used this period."""
        ...

    async def record_usage(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> int:
        """Count one use of a per-period ``metric``; returns the new count."""
        ...


class _Unlimited:
    async def has_feature(
        self, db: AsyncSession, organization_id: int, feature: str
    ) -> bool:
        return True

    async def limit(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> int | None:
        return None

    async def usage(self, db: AsyncSession, organization_id: int, metric: str) -> int:
        return 0

    async def record_usage(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> int:
        return 0


UNLIMITED: Entitlements = _Unlimited()
