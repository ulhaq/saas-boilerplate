from typing import Annotated

from fastapi import Depends

from src.platform.repositories.repository_manager import RepositoryManager
from src.platform.schemas.waitlist import WaitlistJoinIn, WaitlistJoinOut
from src.platform.services.base import BaseService


class WaitlistService(BaseService):
    def __init__(self, repos: Annotated[RepositoryManager, Depends()]) -> None:
        super().__init__(repos)

    async def join(self, schema_in: WaitlistJoinIn) -> WaitlistJoinOut:
        name = schema_in.name.strip() or None if schema_in.name else None

        existing = await self.repos.waitlist_entry.get_by_email(schema_in.email)
        if existing is None:
            await self.repos.waitlist_entry.create(email=schema_in.email, name=name)

        return WaitlistJoinOut(message="You're on the list. We'll be in touch.")
