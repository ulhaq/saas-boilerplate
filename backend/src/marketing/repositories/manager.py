"""Marketing extension of the foundation repository manager."""

from functools import cached_property

from src.foundation.repositories.repository_manager import RepositoryManager
from src.marketing.repositories.waitlist_entry import WaitlistEntryRepository


class MarketingRepositoryManager(RepositoryManager):
    @cached_property
    def waitlist_entry(self) -> WaitlistEntryRepository:
        return WaitlistEntryRepository(self.db)
