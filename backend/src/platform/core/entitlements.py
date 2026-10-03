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

    async def consume(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> bool:
        """Count one use of a per-period ``metric`` if the limit allows it,
        atomically; False when the period's limit is reached."""
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

    async def consume(
        self, db: AsyncSession, organization_id: int, metric: str
    ) -> bool:
        return True


UNLIMITED: Entitlements = _Unlimited()
