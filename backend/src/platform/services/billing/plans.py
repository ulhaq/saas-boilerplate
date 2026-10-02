from typing import Annotated

from fastapi import Depends

from src.platform.billing.dependencies import BillingProviderDep
from src.platform.core.exceptions import NotFoundException
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.billing import PlanOut
from src.platform.services.base import BaseService


class PlanService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
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
