"""Helpers for billing's tests."""

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.billing.models.account import BillingAccount


async def get_billing_account(
    session: AsyncSession,
    organization_id: int,
) -> BillingAccount:
    """The organization's billing account (`src.billing`), in ``session``."""
    rs = await session.execute(
        select(BillingAccount).where(BillingAccount.organization_id == organization_id),
    )
    return rs.scalar_one()
