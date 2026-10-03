"""Marketing extension of the platform repository manager."""

from functools import cached_property

from src.marketing.repositories.waitlist_entry import WaitlistEntryRepository
from src.platform.repositories.repository_manager import RepositoryManager


class MarketingRepositoryManager(RepositoryManager):
    @cached_property
    def waitlist_entry(self) -> WaitlistEntryRepository:
        return WaitlistEntryRepository(self.db)
