"""Example product extension of the foundation repository manager.

Product services and routers depend on this subclass instead of the foundation
``RepositoryManager`` so the foundation stays free of product repositories.
Hook handlers that receive a foundation manager can wrap its session via
``ExampleRepositoryManager(repos.db)`` to join the same transaction.
"""

from functools import cached_property

from src.example.repositories.project import ProjectRepository
from src.foundation.repositories.repository_manager import RepositoryManager


class ExampleRepositoryManager(RepositoryManager):
    @cached_property
    def project(self) -> ProjectRepository:
        return ProjectRepository(self.db)
