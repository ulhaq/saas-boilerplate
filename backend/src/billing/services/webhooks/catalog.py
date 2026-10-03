from src.billing.services.webhooks.base import (
    WebhookHandler,
    WebhookHandlerGroup,
)


class CatalogWebhookHandlers(WebhookHandlerGroup):
    """Products and prices created or edited in the Stripe dashboard."""

    def handlers(self) -> dict[str, WebhookHandler]:
        return {
            "product.created": self._handle_product_created,
            "product.updated": self._handle_product_updated,
            "price.created": self._handle_price_created,
            "price.updated": self._handle_price_updated,
        }

    async def _handle_product_created(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_product_id: str = obj["id"]

        plan = await self.repos.plan.get_by_external_product_id(external_product_id)
        if plan:
            return

        name: str = obj.get("name", external_product_id)
        unlinked = await self.repos.plan.get_unlinked_by_name(name)
        if unlinked:
            await self.repos.plan.update(
                unlinked,
                external_product_id=external_product_id,
            )
            return

        await self.repos.plan.create(
            name=name,
            description=obj.get("description"),
            external_product_id=external_product_id,
        )

    async def _handle_product_updated(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_product_id: str = obj["id"]

        plan = await self.repos.plan.get_by_external_product_id(external_product_id)
        if not plan:
            return

        updates: dict = {}
        if "name" in obj:
            updates["name"] = obj["name"]
        if "description" in obj:
            updates["description"] = obj.get("description")
        if "active" in obj:
            updates["is_active"] = obj["active"]
        if updates:
            await self.repos.plan.update(plan, **updates)

    async def _handle_price_created(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_price_id: str = obj["id"]

        existing = await self.repos.plan_price.get_by_external_price_id(
            external_price_id,
        )
        if existing:
            return

        external_product_id: str | None = obj.get("product")
        if not external_product_id:
            return

        plan = await self.repos.plan.get_by_external_product_id(external_product_id)
        if not plan:
            return

        recurring: dict = obj.get("recurring") or {}
        amount: int = obj.get("unit_amount", 0)
        currency: str = obj.get("currency", "dkk")
        interval: str = recurring.get("interval", "month")
        interval_count: int = recurring.get("interval_count", 1)

        unlinked = await self.repos.plan_price.get_unlinked_by_attributes(
            external_product_id=external_product_id,
            amount=amount,
            currency=currency,
            interval=interval,
            interval_count=interval_count,
        )
        if unlinked:
            await self.repos.plan_price.update(
                unlinked,
                external_price_id=external_price_id,
            )
            return

        await self.repos.plan_price.create(
            plan_id=plan.id,
            amount=amount,
            currency=currency,
            interval=interval,
            interval_count=interval_count,
            external_price_id=external_price_id,
        )

    async def _handle_price_updated(self, raw: dict) -> None:
        obj = raw["data"]["object"]
        external_price_id: str = obj["id"]

        price = await self.repos.plan_price.get_by_external_price_id(external_price_id)
        if not price:
            return

        if "active" in obj:
            await self.repos.plan_price.update(price, is_active=obj["active"])
