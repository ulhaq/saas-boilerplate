from datetime import date
from typing import Annotated

from fastapi import Depends

from src.platform.core.security import Auth
from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.billing import UsageItemOut, UsageOut
from src.platform.services.access import authenticate
from src.platform.services.base import BaseService


class UsageService(BaseService):
    def __init__(
        self,
        repos: Annotated[RepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.current_user = current_user
        super().__init__(repos)

    async def get_current_usage(self) -> UsageOut:
        period_start = date.today().replace(day=1)
        limits = await self.repos.plan_setting.get_settings_for_organization(
            self.current_user.organization_id
        )
        records = await self.repos.plan_usage.get_for_organization(
            self.current_user.organization_id, period_start
        )
        count_by_metric = {r.metric: r.count for r in records}
        usage_items = [
            UsageItemOut(
                metric=limit.key,
                count=count_by_metric.get(limit.key, 0),
                limit=limit.value,
            )
            for limit in limits
        ]
        return UsageOut(period_start=period_start, usage=usage_items)
