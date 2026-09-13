"""
Idempotent deployment script: create Stripe products + prices for all paid
plans and store the resulting IDs in the database.

Run after `alembic upgrade head` on every first-time deployment (safe to
re-run - already-linked plans are skipped):

    python -m src.platform.billing.stripe_setup
"""

import asyncio
import logging
from typing import Literal, cast

from sqlalchemy import select

from src.platform.billing.stripe_provider import StripeProvider
from src.platform.core.config import settings
from src.platform.core.database import ASYNC_SESSION_LOCAL
from src.platform.core.exceptions import BillingProviderException
from src.platform.core.logging import setup_logging
from src.platform.models.billing import Plan

setup_logging("stripe_setup")
log = logging.getLogger(__name__)


async def setup() -> None:
    provider = StripeProvider(
        api_key=settings.stripe_secret_key.get_secret_value(),
        webhook_secret=settings.stripe_webhook_secret.get_secret_value(),
    )

    async with ASYNC_SESSION_LOCAL() as session:
        result = await session.execute(
            select(Plan).where(Plan.deleted_at.is_(None), Plan.is_active.is_(True))
        )
        plans = result.scalars().all()

        for plan in plans:
            if all(p.amount == 0 for p in plan.prices):
                log.info(
                    "Skipping free plan '%s' (no Stripe product needed)", plan.name
                )
                continue

            if plan.external_product_id:
                log.info(
                    "Plan '%s' already linked to Stripe product %s, skipping",
                    plan.name,
                    plan.external_product_id,
                )
            else:
                existing = await provider.search_product_by_name(plan.name)
                if existing:
                    already_owned = await session.execute(
                        select(Plan).where(
                            Plan.external_product_id == existing.external_id,
                            Plan.id != plan.id,
                        )
                    )
                    if already_owned.scalars().first() is not None:
                        log.warning(
                            "Stripe product %s already linked to a different plan, "
                            "skipping plan '%s'",
                            existing.external_id,
                            plan.name,
                        )
                        continue
                    if not existing.is_active:
                        product = await provider.create_product(
                            plan.name, plan.description
                        )
                        plan.external_product_id = product.external_id
                        log.info(
                            "Archived product found; created new Stripe product %s "
                            "for plan '%s'",
                            product.external_id,
                            plan.name,
                        )
                    else:
                        plan.external_product_id = existing.external_id
                        log.info(
                            "Linked existing Stripe product %s to plan '%s'",
                            existing.external_id,
                            plan.name,
                        )
                else:
                    product = await provider.create_product(plan.name, plan.description)
                    plan.external_product_id = product.external_id
                    log.info(
                        "Created Stripe product %s for plan '%s'",
                        product.external_id,
                        plan.name,
                    )

            if plan.external_product_id is None:
                raise BillingProviderException(
                    f"Plan {plan.id} has no external product ID after sync"
                )
            plan_external_product_id = plan.external_product_id

            for price in plan.prices:
                if price.external_price_id:
                    log.info(
                        "Price %s already linked to Stripe price %s, skipping",
                        price.id,
                        price.external_price_id,
                    )
                    continue

                interval_literal = cast(
                    Literal["day", "month", "week", "year"], price.interval
                )
                existing_price = await provider.search_price(
                    external_product_id=plan_external_product_id,
                    amount=price.amount,
                    currency=price.currency,
                    interval=interval_literal,
                    interval_count=price.interval_count,
                )
                if existing_price and existing_price.is_active:
                    price.external_price_id = existing_price.external_id
                    log.info(
                        "Linked existing Stripe price %s to plan '%s' (%s %s/%s)",
                        existing_price.external_id,
                        plan.name,
                        price.amount,
                        price.currency.upper(),
                        price.interval,
                    )
                else:
                    if existing_price and not existing_price.is_active:
                        log.info(
                            "Archived price found for plan '%s'; creating new one",
                            plan.name,
                        )
                    stripe_price = await provider.create_price(
                        external_product_id=plan_external_product_id,
                        amount=price.amount,
                        currency=price.currency,
                        interval=interval_literal,
                        interval_count=price.interval_count,
                    )
                    price.external_price_id = stripe_price.external_id
                    log.info(
                        "Created Stripe price %s for plan '%s' (%s %s/%s)",
                        stripe_price.external_id,
                        plan.name,
                        price.amount,
                        price.currency.upper(),
                        price.interval,
                    )

        await session.commit()
        log.info("Stripe setup complete")


if __name__ == "__main__":
    asyncio.run(setup())
