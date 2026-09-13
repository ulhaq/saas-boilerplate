from collections.abc import Sequence
from copy import copy
from datetime import UTC, datetime
from typing import Any, ClassVar, Literal, Self, overload

from sqlalchemy import (
    BinaryExpression,
    Select,
    String,
    and_,
    cast,
    func,
    or_,
    select,
)
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.sql.elements import ColumnElement, UnaryExpression

from src.platform.core.exceptions import NotFoundException, UnscopedQueryError
from src.platform.models.mixins import ResourceModel, ResourceModelBase
from src.platform.repositories import utils
from src.platform.repositories.abc import ResourceRepositoryABC, SoftDeleteRepositoryABC
from src.platform.schemas.common import FilterItem


class SQLResourceRepository[ModelType: ResourceModelBase](
    ResourceRepositoryABC[ModelType]
):
    search_fields: ClassVar[list[str]] = []

    async def get_one(self, identifier: int) -> ModelType:
        stmt = select(self.model).filter(self.model.id == identifier)
        rs = await self.db.execute(stmt)
        try:
            return rs.unique().scalar_one()
        except NoResultFound as exc:
            raise NotFoundException(
                f"{self.model.__name__} not found. [{identifier=}]"
            ) from exc

    async def get(self, identifier: int) -> ModelType | None:
        stmt = select(self.model).filter(self.model.id == identifier)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def get_all(self) -> Sequence[ModelType]:
        stmt = select(self.model)
        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def filter_by(self, **kwargs: Any) -> Sequence[ModelType]:
        stmt = select(self.model).filter_by(**kwargs)
        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def filter_by_ids(self, identifiers: list[int]) -> Sequence[ModelType]:
        stmt = select(self.model).filter(self.model.id.in_(identifiers))
        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def exists(self, identifier: int) -> bool:
        stmt = select(self.model).filter(self.model.id == identifier)
        rs = await self.db.execute(select(stmt.exists()))
        return rs.scalar_one()

    async def create(self, **kwargs: Any) -> ModelType:
        instance = self.model(**kwargs)

        instance.created_at = datetime.now(UTC)
        instance.updated_at = datetime.now(UTC)

        self.db.add(instance)

        return await self.save(instance)

    async def update(self, model: ModelType, **kwargs: Any) -> ModelType:
        for attr, value in kwargs.items():
            setattr(model, attr, value)
        model.updated_at = datetime.now(UTC)

        self.db.add(model)

        return await self.save(model)

    async def force_delete(self, model: ModelType) -> None:
        await self.db.delete(model)

        await self.save()

    async def paginate(
        self,
        sort: list[str],
        filters: list[FilterItem],
        page_size: int,
        page_number: int,
        search: str | None = None,
    ) -> tuple[Sequence[ModelType], int]:
        order_expressions = self._get_order_expressions(sort)
        filter_expressions = self._get_filter_expressions(filters)
        search_expressions = self._get_search_expressions(search)

        stmt = select(self.model)

        if filter_expressions:
            stmt = stmt.filter(*filter_expressions)
        if search_expressions:
            stmt = stmt.filter(or_(*search_expressions))

        stmt = (
            stmt.order_by(*order_expressions)
            .offset((page_number - 1) * page_size)
            .limit(page_size)
        )

        rs = await self.db.execute(stmt)
        items = rs.unique().scalars().all()

        combined = [
            *([and_(*filter_expressions)] if filter_expressions else []),
            *([or_(*search_expressions)] if search_expressions else []),
        ]
        total = await self.get_total(*combined)

        return items, total

    async def get_total(self, *filter_expressions: ColumnElement[bool]) -> int:
        stmt = select(func.count()).select_from(self.model)

        if filter_expressions:
            stmt = stmt.filter(*filter_expressions)

        rs = await self.db.execute(stmt)
        total = rs.scalar_one()
        return int(total)

    def _get_search_expressions(self, search: str | None) -> list[BinaryExpression]:
        if not search or not self.search_fields:
            return []
        return [
            cast(getattr(self.model, field), String).ilike(f"%{search}%")
            for field in self.search_fields
            if hasattr(self.model, field)
        ]

    async def add_relationship(
        self,
        target_model: ModelType,
        related_model: Any,
        relationship_attr: str,
        *related_ids: int,
    ) -> None:
        stmt = select(related_model).filter(related_model.id.in_(related_ids))
        rs = await self.db.execute(stmt)
        related_objects = rs.unique().scalars().all()

        if related_objects:
            current_value = getattr(target_model, relationship_attr)

            if isinstance(current_value, list):
                current_value.extend(related_objects)
            else:
                setattr(target_model, relationship_attr, related_objects[0])

        await self.save(target_model)

    async def remove_relationship(
        self,
        target_model: ModelType,
        relationship_attr: str,
        *related_ids: int,
    ) -> None:
        current_value = getattr(target_model, relationship_attr)

        if isinstance(current_value, list):
            setattr(
                target_model,
                relationship_attr,
                [
                    related_obj
                    for related_obj in current_value
                    if related_obj.id not in related_ids
                ],
            )
        else:
            setattr(target_model, relationship_attr, None)

        await self.save(target_model)

    @overload
    async def save(
        self,
        instance: None = None,
        *,
        refresh: bool = True,
    ) -> None: ...
    @overload
    async def save[I](
        self,
        instance: I,
        *,
        refresh: Literal[True] = True,
    ) -> I: ...
    @overload
    async def save[I](
        self,
        instance: I,
        *,
        refresh: Literal[False],
    ) -> None: ...
    async def save[I](
        self,
        instance: I | None = None,
        *,
        refresh: bool = True,
    ) -> I | None:
        await self.db.flush()

        if instance is None:
            return None

        if refresh:
            await self.db.refresh(instance)
            return instance

        return None

    def _get_order_expressions(self, sort: list[str]) -> list[UnaryExpression]:
        ordering: list[UnaryExpression] = []

        for field_name in sort:
            field_name = field_name.lstrip("+")
            descending = field_name.startswith("-")
            field_name = field_name.lstrip("-")

            field = getattr(self.model, field_name, None)
            if not isinstance(field, InstrumentedAttribute):
                raise ValueError(f"Invalid sort value: {field_name}")

            ordering.append(field.asc() if not descending else field.desc())

        return ordering

    def _get_filter_expressions(
        self, filters: list[FilterItem]
    ) -> list[BinaryExpression]:
        expressions = []
        for f in filters:
            if not f.values:
                continue

            field = getattr(self.model, f.field, None)
            if not field or not hasattr(field, "type"):
                raise ValueError(f"Invalid filtering field: {f.field}")

            field_type = field.type.python_type
            if f.op not in utils.FILTER_OPERATORS_BY_FIELD_TYPE.get(field_type, []):
                raise ValueError(
                    f"Operator '{f.op.value}' not supported "
                    f"for '{field_type.__name__}' type"
                )

            values = utils.cast_values_to_type(f.values, field_type, f.field, f.op)

            expr = utils.get_filter_expression(f.op, values, field)
            if expr is not None:
                if isinstance(expr, list):
                    expressions.extend(expr)
                else:
                    expressions.append(expr)

        return expressions

    def _include_deleted(self, stmt: Select, include_deleted: bool = False) -> Select:
        deleted_at = getattr(self.model, "deleted_at", None)
        if include_deleted is False and deleted_at is not None:
            return stmt.filter(deleted_at.is_(None))
        return stmt


class SoftDeleteRepository[ModelType: ResourceModel](
    SQLResourceRepository[ModelType], SoftDeleteRepositoryABC[ModelType]
):
    async def get_one(
        self, identifier: int, include_deleted: bool = False
    ) -> ModelType:
        stmt = select(self.model).filter(self.model.id == identifier)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        try:
            return rs.unique().scalar_one()
        except NoResultFound as exc:
            raise NotFoundException(
                f"{self.model.__name__} not found. [{identifier=}]"
            ) from exc

    async def get(
        self, identifier: int, include_deleted: bool = False
    ) -> ModelType | None:
        stmt = select(self.model).filter(self.model.id == identifier)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def _get_by_field(
        self, field: str, value: Any, include_deleted: bool = False
    ) -> ModelType | None:
        stmt = select(self.model).filter(getattr(self.model, field) == value)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def get_all(self, include_deleted: bool = False) -> Sequence[ModelType]:
        stmt = select(self.model)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def filter_by(
        self, include_deleted: bool = False, **kwargs: Any
    ) -> Sequence[ModelType]:
        stmt = select(self.model).filter_by(**kwargs)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def filter_by_ids(
        self, identifiers: list[int], include_deleted: bool = False
    ) -> Sequence[ModelType]:
        stmt = select(self.model).filter(self.model.id.in_(identifiers))
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def exists(self, identifier: int, include_deleted: bool = False) -> bool:
        stmt = select(self.model).filter(self.model.id == identifier)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(select(stmt.exists()))
        return rs.scalar_one()

    async def paginate(
        self,
        sort: list[str],
        filters: list[FilterItem],
        page_size: int,
        page_number: int,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[Sequence[ModelType], int]:
        order_expressions = self._get_order_expressions(sort)
        filter_expressions = self._get_filter_expressions(filters)
        search_expressions = self._get_search_expressions(search)

        stmt = select(self.model)

        if filter_expressions:
            stmt = stmt.filter(*filter_expressions)
        if search_expressions:
            stmt = stmt.filter(or_(*search_expressions))

        stmt = self._include_deleted(stmt, include_deleted)

        stmt = (
            stmt.order_by(*order_expressions)
            .offset((page_number - 1) * page_size)
            .limit(page_size)
        )

        rs = await self.db.execute(stmt)
        items = rs.unique().scalars().all()

        combined = [
            *([and_(*filter_expressions)] if filter_expressions else []),
            *([or_(*search_expressions)] if search_expressions else []),
        ]
        total = await self.get_total(*combined, include_deleted=include_deleted)

        return items, total

    async def get_total(
        self, *filter_expressions: ColumnElement[bool], include_deleted: bool = False
    ) -> int:
        stmt = select(func.count()).select_from(self.model)

        if filter_expressions:
            stmt = stmt.filter(*filter_expressions)

        stmt = self._include_deleted(stmt, include_deleted)

        rs = await self.db.execute(stmt)
        total = rs.scalar_one()
        return int(total)

    async def delete(self, model: ModelType) -> None:
        model.deleted_at = datetime.now(UTC)
        await self.save()

    async def restore(self, model: ModelType) -> ModelType:
        model.deleted_at = None
        model.updated_at = datetime.now(UTC)
        self.db.add(model)
        return await self.save(model)


class OrganizationScopedRepository[ModelType: ResourceModel](
    SoftDeleteRepository[ModelType]
):
    """Repository whose generic queries are tenant-scoped by default.

    Querying without a scope raises UnscopedQueryError - forgetting to scope
    must fail loudly, not silently return cross-tenant data. Code that
    legitimately needs cross-tenant access (auth identity lookups, workers,
    webhook handlers) must opt out explicitly via `.unscoped`.
    """

    _organization_id: int | None = None
    _allow_unscoped: bool = False

    def set_organization_scope(self, organization_id: int) -> None:
        self._organization_id = organization_id

    @property
    def unscoped(self) -> Self:
        """A copy of this repository that may run cross-tenant queries."""
        clone = copy(self)
        clone._organization_id = None
        clone._allow_unscoped = True
        return clone

    def _scope_filter(self, stmt: Select, organization_id: int) -> Select:
        """How the tenant filter is applied; override for join-based scoping."""
        return stmt.filter(self.model.organization_id == organization_id)  # ty: ignore[unresolved-attribute]

    def _apply_organization_scope(self, stmt: Select) -> Select:
        if self._organization_id is not None:
            return self._scope_filter(stmt, self._organization_id)
        if self._allow_unscoped:
            return stmt
        raise UnscopedQueryError(
            f"{type(self).__name__} was queried without an organization scope. "
            "Call set_organization_scope(organization_id) first, or use "
            "`.unscoped` for an intentional cross-tenant query."
        )

    async def get_one(
        self, identifier: int, include_deleted: bool = False
    ) -> ModelType:
        stmt = select(self.model).filter(self.model.id == identifier)
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt, include_deleted)

        rs = await self.db.execute(stmt)
        try:
            return rs.unique().scalar_one()
        except NoResultFound as exc:
            raise NotFoundException(
                f"{self.model.__name__} not found. [{identifier=}]"
            ) from exc

    async def get(
        self, identifier: int, include_deleted: bool = False
    ) -> ModelType | None:
        stmt = select(self.model).filter(self.model.id == identifier)
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt, include_deleted)

        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def _get_by_field(
        self, field: str, value: Any, include_deleted: bool = False
    ) -> ModelType | None:
        stmt = select(self.model).filter(getattr(self.model, field) == value)
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(stmt)
        return rs.unique().scalar_one_or_none()

    async def get_all(self, include_deleted: bool = False) -> Sequence[ModelType]:
        stmt = select(self.model)
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt, include_deleted)

        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def filter_by(
        self, include_deleted: bool = False, **kwargs: Any
    ) -> Sequence[ModelType]:
        stmt = select(self.model).filter_by(**kwargs)
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt, include_deleted)

        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def filter_by_ids(
        self, identifiers: list[int], include_deleted: bool = False
    ) -> Sequence[ModelType]:
        stmt = select(self.model).filter(self.model.id.in_(identifiers))
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt, include_deleted)

        rs = await self.db.execute(stmt)
        return rs.unique().scalars().all()

    async def exists(self, identifier: int, include_deleted: bool = False) -> bool:
        stmt = select(self.model).filter(self.model.id == identifier)
        stmt = self._apply_organization_scope(stmt)
        stmt = self._include_deleted(stmt, include_deleted)
        rs = await self.db.execute(select(stmt.exists()))
        return rs.scalar_one()

    async def create(self, **kwargs: Any) -> ModelType:
        if self._organization_id is not None:
            kwargs.setdefault("organization_id", self._organization_id)
        return await super().create(**kwargs)

    async def paginate(
        self,
        sort: list[str],
        filters: list[FilterItem],
        page_size: int,
        page_number: int,
        search: str | None = None,
        include_deleted: bool = False,
    ) -> tuple[Sequence[ModelType], int]:
        order_expressions = self._get_order_expressions(sort)
        filter_expressions = self._get_filter_expressions(filters)
        search_expressions = self._get_search_expressions(search)

        stmt = select(self.model)
        stmt = self._apply_organization_scope(stmt)

        if filter_expressions:
            stmt = stmt.filter(*filter_expressions)
        if search_expressions:
            stmt = stmt.filter(or_(*search_expressions))

        stmt = self._include_deleted(stmt, include_deleted)

        stmt = (
            stmt.order_by(*order_expressions)
            .offset((page_number - 1) * page_size)
            .limit(page_size)
        )

        rs = await self.db.execute(stmt)
        items = rs.unique().scalars().all()

        combined = [
            *([and_(*filter_expressions)] if filter_expressions else []),
            *([or_(*search_expressions)] if search_expressions else []),
        ]
        total = await self.get_total(*combined, include_deleted=include_deleted)

        return items, total

    async def get_total(
        self, *filter_expressions: ColumnElement[bool], include_deleted: bool = False
    ) -> int:
        stmt = select(func.count()).select_from(self.model)

        stmt = self._apply_organization_scope(stmt)

        if filter_expressions:
            stmt = stmt.filter(*filter_expressions)

        stmt = self._include_deleted(stmt, include_deleted)

        rs = await self.db.execute(stmt)
        total = rs.scalar_one()
        return int(total)
