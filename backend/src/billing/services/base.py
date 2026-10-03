from src.billing.repositories.manager import BillingRepositoryManager
from src.platform.services.base import BaseService


class BillingBaseService(BaseService):
    """A service with the billing repositories on ``self.repos``."""

    repos: BillingRepositoryManager

    def __init__(self, repos: BillingRepositoryManager) -> None:
        super().__init__(repos)
