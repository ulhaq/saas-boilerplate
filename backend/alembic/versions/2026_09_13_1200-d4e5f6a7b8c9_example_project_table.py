"""example product: project table

Revision ID: d4e5f6a7b8c9
Revises: 2c3b2ee136dc
Create Date: 2026-09-13 12:00:00.000000

"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "2c3b2ee136dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_billing_plan_setting_table = sa.table(
    "billing_plan_setting",
    sa.column("plan_id", sa.Integer),
    sa.column("key", sa.String),
    sa.column("value", sa.Integer),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
    sa.column("deleted_at", sa.DateTime),
)

# Project limit per seeded plan (plan ids from the initial migration).
_PROJECT_LIMITS = {1: 3, 2: 20, 3: 100, 4: None}


def upgrade() -> None:
    op.create_table(
        "project",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_project_organization_id", "project", ["organization_id"])

    now = datetime.now(UTC)
    op.bulk_insert(
        _billing_plan_setting_table,
        [
            {
                "plan_id": plan_id,
                "key": "projects",
                "value": value,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
            for plan_id, value in _PROJECT_LIMITS.items()
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.delete(_billing_plan_setting_table).where(
            _billing_plan_setting_table.c.key == "projects"
        )
    )
    op.drop_index("ix_project_organization_id", table_name="project")
    op.drop_table("project")
