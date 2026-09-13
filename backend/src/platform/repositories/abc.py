from abc import ABC, abstractmethod
from collections.abc import Sequence
from typing import Any

from src.platform.models.mixins import ResourceModel
from src.platform.schemas.common import FilterItem


class RepositoryABC[ModelType](ABC):
    model: type[ModelType]
    db: Any

    def __init__(self, model: type[ModelType], db: Any) -> None:
        self.model = model
        self.db = db


class ResourceRepositoryABC[ModelType](RepositoryABC[ModelType], ABC):
    @abstractmethod
    async def get_one(self, identifier: int) -> ModelType: ...

    @abstractmethod
    async def get(self, identifier: int) -> ModelType | None: ...

    @abstractmethod
    async def get_all(self) -> Sequence[ModelType]: ...

    @abstractmethod
    async def filter_by(self, **kwargs: Any) -> Sequence[ModelType]: ...

    @abstractmethod
    async def filter_by_ids(self, identifiers: list[int]) -> Sequence[ModelType]: ...

    @abstractmethod
    async def exists(self, identifier: int) -> bool: ...

    @abstractmethod
    async def create(self, **kwargs: Any) -> ModelType: ...

    @abstractmethod
    async def update(self, model: ModelType, **kwargs: Any) -> ModelType: ...

    @abstractmethod
    async def force_delete(self, model: ModelType) -> None: ...

    @abstractmethod
    async def paginate(
        self,
        sort: list[str],
        filters: list[FilterItem],
        page_size: int,
        page_number: int,
        search: str | None = None,
    ) -> tuple[Sequence[ModelType], int]: ...

    @abstractmethod
    async def get_total(self, *filter_expressions: Any) -> int: ...


class SoftDeleteRepositoryABC[ModelType: ResourceModel](
    ResourceRepositoryABC[ModelType], ABC
):
    @abstractmethod
    async def get_one(
        self, identifier: int, include_deleted: bool = False
    ) -> ModelType: ...

    @abstractmethod
    async def get(
        self, identifier: int, include_deleted: bool = False
    ) -> ModelType | None: ...

    @abstractmethod
    async def get_all(self, include_deleted: bool = False) -> Sequence[ModelType]: ...

    @abstractmethod
    async def filter_by(
        self, include_deleted: bool = False, **kwargs: Any
    ) -> Sequence[ModelType]: ...

    @abstractmethod
    async def filter_by_ids(
        self, identifiers: list[int], include_deleted: bool = False
    ) -> Sequence[ModelType]: ...

    @abstractmethod
    async def exists(self, identifier: int, include_deleted: bool = False) -> bool: ...

    @abstractmethod
    async def paginate(
        self,
        sort: list[str],
        filters: list[FilterItem],
        page_size: int,
        page_number: int,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[Sequence[ModelType], int]: ...

    @abstractmethod
    async def get_total(
        self, *filter_expressions: Any, include_deleted: bool = False
    ) -> int: ...

    @abstractmethod
    async def delete(self, model: ModelType) -> None: ...

    @abstractmethod
    async def restore(self, model: ModelType) -> ModelType: ...
