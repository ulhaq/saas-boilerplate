"""Example product extension of the platform repository manager.

Product services and routers depend on this subclass instead of the platform
``RepositoryManager`` so the platform stays free of product repositories.
Hook handlers that receive a platform manager can wrap its session via
``ExampleRepositoryManager(repos.db)`` to join the same transaction.
"""

from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from src.example.repositories.project import ProjectRepository
from src.platform.core.database import get_db
from src.platform.repositories.repository_manager import RepositoryManager


class ExampleRepositoryManager(RepositoryManager):
    def __init__(self, db: Annotated[AsyncSession, Depends(get_db)]) -> None:
        super().__init__(db)
        self._project: ProjectRepository | None = None

    @property
    def project(self) -> ProjectRepository:
        if self._project is None:
            self._project = ProjectRepository(self.db)
        return self._project
