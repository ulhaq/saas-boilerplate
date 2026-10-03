"""billing module: accounts, plans, subscriptions, usage, webhook events

Revision ID: b1c2d3e4f5a6
Revises: 2c3b2ee136dc
Create Date: 2025-06-22 15:59:00.000000

Owned by `src.billing`; seeds the plans, their prices, the api_token feature
and the platform's seat limits. Drop this file (and point the next revision at
the initial schema) to run without billing.
"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op

revision: str = "b1c2d3e4f5a6"
down_revision: str | None = "2c3b2ee136dc"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_SUBSCRIPTION_STATUSES = (
    "incomplete",
    "incomplete_expired",
    "active",
    "trialing",
    "past_due",
    "canceled",
    "unpaid",
    "paused",
)


def upgrade() -> None:
    # ── billing tables ─────────────────────────────────────────────────────────

    op.create_table(
        "billing_account",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("external_customer_id", sa.String(), nullable=True),
        sa.Column("billing_email", sa.String(), nullable=False),
        sa.Column(
            "has_payment_method", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column("trial_used", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("trial_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("organization_id"),
    )
    op.create_index(
        "ix_billing_account_external_customer_id",
        "billing_account",
        ["external_customer_id"],
        unique=True,
    )

    billing_plan_table = op.create_table(
        "billing_plan",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("external_product_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_billing_plan_name", "billing_plan", ["name"])
    op.create_index(
        "ix_billing_plan_external_product_id",
        "billing_plan",
        ["external_product_id"],
        unique=True,
    )

    billing_plan_price_table = op.create_table(
        "billing_plan_price",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("billing_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("interval", sa.String(), nullable=False),
        sa.Column("interval_count", sa.Integer(), nullable=False, default=1),
        sa.Column("external_price_id", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, default=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_billing_plan_price_plan_id", "billing_plan_price", ["plan_id"])
    op.create_index(
        "ix_billing_plan_price_external_price_id",
        "billing_plan_price",
        ["external_price_id"],
        unique=True,
    )

    op.create_table(
        "billing_subscription",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "plan_price_id",
            sa.Integer(),
            sa.ForeignKey("billing_plan_price.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("external_subscription_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False, default="incomplete"),
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, default=False),
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trial_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            f"status IN {_SUBSCRIPTION_STATUSES}",
            name="ck_billing_subscription_status",
        ),
    )
    op.create_index(
        "ix_billing_subscription_organization_id",
        "billing_subscription",
        ["organization_id"],
    )
    op.create_index(
        "ix_billing_subscription_external_subscription_id",
        "billing_subscription",
        ["external_subscription_id"],
        unique=True,
    )
    op.create_index(
        "uq_billing_subscription_active_organization",
        "billing_subscription",
        ["organization_id"],
        unique=True,
        postgresql_where=sa.text("status != 'canceled' AND deleted_at IS NULL"),
    )

    op.create_table(
        "billing_webhook_event",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("external_event_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, default="received"),
        sa.Column("error", sa.String(), nullable=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_billing_webhook_event_external_event_id",
        "billing_webhook_event",
        ["external_event_id"],
        unique=True,
    )

    billing_plan_feature_table = op.create_table(
        "billing_plan_feature",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("billing_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("feature", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("plan_id", "feature", name="uq_billing_plan_feature"),
    )
    op.create_index(
        "ix_billing_plan_feature_plan_id", "billing_plan_feature", ["plan_id"]
    )
    op.create_index(
        "ix_billing_plan_feature_feature", "billing_plan_feature", ["feature"]
    )

    billing_plan_setting_table = op.create_table(
        "billing_plan_setting",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "plan_id",
            sa.Integer(),
            sa.ForeignKey("billing_plan.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("key", sa.String(), nullable=False),
        sa.Column("value", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("plan_id", "key", name="uq_billing_plan_setting"),
    )
    op.create_index(
        "ix_billing_plan_setting_plan_id", "billing_plan_setting", ["plan_id"]
    )
    op.create_index("ix_billing_plan_setting_key", "billing_plan_setting", ["key"])

    op.create_table(
        "billing_plan_usage",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "organization_id",
            sa.Integer(),
            sa.ForeignKey("organization.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("metric", sa.String(), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_id",
            "metric",
            "period_start",
            name="uq_billing_plan_usage",
        ),
    )
    op.create_index(
        "ix_billing_plan_usage_organization_id",
        "billing_plan_usage",
        ["organization_id"],
    )

    now = datetime.now(UTC)

    # ── seed plans + prices ──────────────────────────────────────────

    op.bulk_insert(
        billing_plan_table,
        [
            {
                "name": "Free",
                "description": "For individuals getting started",
                "external_product_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "name": "Basic",
                "description": "For small teams",
                "external_product_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "name": "Advanced",
                "description": "For growing teams that need API access",
                "external_product_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "name": "Pro",
                "description": "For large organizations",
                "external_product_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )
    op.bulk_insert(
        billing_plan_price_table,
        [
            {
                "plan_id": 1,
                "amount": 0,
                "currency": "dkk",
                "interval": "month",
                "interval_count": 1,
                "external_price_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "plan_id": 2,
                "amount": 7900,
                "currency": "dkk",
                "interval": "month",
                "interval_count": 1,
                "external_price_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "plan_id": 3,
                "amount": 19900,
                "currency": "dkk",
                "interval": "month",
                "interval_count": 1,
                "external_price_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
            {
                "plan_id": 4,
                "amount": 49900,
                "currency": "dkk",
                "interval": "month",
                "interval_count": 1,
                "external_price_id": None,
                "is_active": True,
                "deleted_at": None,
                "created_at": now,
                "updated_at": now,
            },
        ],
    )

    # Advanced and Pro plans get the api_token feature
    op.bulk_insert(
        billing_plan_feature_table,
        [
            {
                "plan_id": 3,
                "feature": "api_token",
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            },
            {
                "plan_id": 4,
                "feature": "api_token",
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            },
        ],
    )

    # Seat limits per plan (platform `UsageMetric.SEATS`)
    op.bulk_insert(
        billing_plan_setting_table,
        [
            {
                "plan_id": plan_id,
                "key": "seats",
                "value": seats,
                "created_at": now,
                "updated_at": now,
                "deleted_at": None,
            }
            for plan_id, seats in {1: 1, 2: 3, 3: 10, 4: 50}.items()
        ],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_plan_usage_organization_id", table_name="billing_plan_usage"
    )
    op.drop_table("billing_plan_usage")

    op.drop_index("ix_billing_plan_setting_key", table_name="billing_plan_setting")
    op.drop_index("ix_billing_plan_setting_plan_id", table_name="billing_plan_setting")
    op.drop_table("billing_plan_setting")

    op.drop_index("ix_billing_plan_feature_feature", table_name="billing_plan_feature")
    op.drop_index("ix_billing_plan_feature_plan_id", table_name="billing_plan_feature")
    op.drop_table("billing_plan_feature")

    op.drop_index(
        "ix_billing_webhook_event_external_event_id",
        table_name="billing_webhook_event",
    )
    op.drop_table("billing_webhook_event")

    op.drop_index(
        "uq_billing_subscription_active_organization",
        table_name="billing_subscription",
    )
    op.drop_index(
        "ix_billing_subscription_external_subscription_id",
        table_name="billing_subscription",
    )
    op.drop_index(
        "ix_billing_subscription_organization_id", table_name="billing_subscription"
    )
    op.drop_table("billing_subscription")

    op.drop_index(
        "ix_billing_plan_price_external_price_id", table_name="billing_plan_price"
    )
    op.drop_index("ix_billing_plan_price_plan_id", table_name="billing_plan_price")
    op.drop_table("billing_plan_price")

    op.drop_index("ix_billing_plan_external_product_id", table_name="billing_plan")
    op.drop_index("ix_billing_plan_name", table_name="billing_plan")
    op.drop_table("billing_plan")

    op.drop_index(
        "ix_billing_account_external_customer_id", table_name="billing_account"
    )
    op.drop_table("billing_account")
