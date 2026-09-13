from typing import Annotated

from fastapi import Depends

from src.example.enums import ExampleAuditAction, ExampleErrorCode, ExampleUsageMetric
from src.example.models.project import Project
from src.example.repositories.manager import ExampleRepositoryManager
from src.example.repositories.project import ProjectRepository
from src.example.schemas.project import ProjectIn, ProjectOut, ProjectPatch
from src.platform.core.dependencies import authenticate
from src.platform.core.exceptions import AlreadyExistsException
from src.platform.core.security import Auth
from src.platform.services.base import ResourceService


class ProjectService(
    ResourceService[ProjectRepository, Project, ProjectIn | ProjectPatch, ProjectOut]
):
    current_user: Auth

    def __init__(
        self,
        repos: Annotated[ExampleRepositoryManager, Depends()],
        current_user: Annotated[Auth, Depends(authenticate)],
    ) -> None:
        self.repo = repos.project
        self.repo.set_organization_scope(current_user.organization_id)
        self.current_user = current_user
        super().__init__(repos)

    async def _assert_name_available(
        self, name: str, exclude_id: int | None = None
    ) -> None:
        existing = await self.repo.get_by_name(name)
        if existing is not None and existing.id != exclude_id:
            raise AlreadyExistsException(
                f"Project already exists. [name={name}]",
                error_code=ExampleErrorCode.PROJECT_NAME_TAKEN,
            )

    async def create_project(self, schema_in: ProjectIn) -> ProjectOut:
        async def validate() -> None:
            await self._require_capacity(
                ExampleUsageMetric.PROJECTS,
                self.current_user.organization_id,
                await self.repo.count(),
            )
            await self._assert_name_available(schema_in.name)

        project = await super().create(schema_in, validate)
        await self.log_audit(
            ExampleAuditAction.PROJECT_CREATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="project",
            resource_id=project.id,
            details={"name": project.name},
        )
        return ProjectOut.model_validate(project)

    async def patch_project(
        self, identifier: int, schema_in: ProjectPatch
    ) -> ProjectOut:
        async def validate() -> None:
            if schema_in.name is not None:
                await self._assert_name_available(schema_in.name, exclude_id=identifier)

        project = await super().patch(identifier, schema_in, validate)
        await self.log_audit(
            ExampleAuditAction.PROJECT_UPDATE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="project",
            resource_id=project.id,
            details=schema_in.model_dump(exclude_unset=True),
        )
        return ProjectOut.model_validate(project)

    async def delete_project(self, identifier: int) -> None:
        await super().delete(identifier)
        await self.log_audit(
            ExampleAuditAction.PROJECT_DELETE,
            organization_id=self.current_user.organization_id,
            user_id=self.current_user.id,
            resource_type="project",
            resource_id=identifier,
        )
