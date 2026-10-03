from typing import Annotated

from fastapi import Depends

from src.billing.provider.dependencies import BillingProviderDep
from src.billing.repositories.manager import BillingRepositoryManager
from src.billing.schemas.billing import PlanOut
from src.billing.services.base import BillingBaseService
from src.platform.core.exceptions import NotFoundException


class PlanService(BillingBaseService):
    def __init__(
        self,
        repos: Annotated[BillingRepositoryManager, Depends()],
        provider: BillingProviderDep,
    ) -> None:
        self.provider = provider
        super().__init__(repos)

    async def get_plan(self, plan_id: int) -> PlanOut:
        plan = await self.repos.plan.get(plan_id)
        if not plan:
            raise NotFoundException(f"Plan not found. [plan_id={plan_id}]")
        return PlanOut.model_validate(plan)

    async def get_all_plans(self) -> list[PlanOut]:
        plans = await self.repos.plan.get_active_plans()
        return [PlanOut.model_validate(p) for p in plans]
