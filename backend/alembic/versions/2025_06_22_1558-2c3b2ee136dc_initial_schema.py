"""initial_schema

Revision ID: 2c3b2ee136dc
Revises:
Create Date: 2025-06-22 15:58:50.524796

"""

from collections.abc import Sequence
from datetime import UTC, datetime

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql
from src.bootstrap import ALL_PERMISSIONS, PERMISSION_DESCRIPTIONS

revision: str = "2c3b2ee136dc"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Auto-increment id sequences start here (260614 = YYMMDD).
SEQUENCE_START = 260614

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

_permission_table = sa.table(
    "permission",
    sa.Column("name", sa.String),
    sa.Column("description", sa.String),
    sa.Column("created_at", sa.DateTime),
    sa.Column("updated_at", sa.DateTime),
)


def upgrade() -> None:
    # ── standalone tables ──────────────────────────────────────────────────────

    op.create_table(
        "organization",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("external_customer_id", sa.String(), nullable=True),
        sa.Column("billing_email", sa.String(), nullable=False),
        sa.Column(
            "has_payment_method", sa.Boolean(), nullable=False, server_default="0"
        ),
        sa.Column("trial_used", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("trial_reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_organization_name"), "organization", ["name"])
    op.create_index(
        "ix_organization_external_customer_id",
        "organization",
        ["external_customer_id"],
        unique=True,
    )

    op.create_table(
        "permission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_permission_name"), "permission", ["name"], unique=True)

    # ── user & role ────────────────────────────────────────────────────────────

    op.create_table(
        "user",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("password", sa.String(), nullable=False),
        sa.Column("locale", sa.String(length=8), nullable=False, server_default="da"),
        sa.Column("theme", sa.String(length=16), nullable=False, server_default="system"),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_user_name"), "user", ["name"])

    op.create_table(
        "role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("is_protected", sa.Boolean(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization.id"],
            name="fk_role_organization_id_organization",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_role_name"), "role", ["name"])

    # ── junction tables ────────────────────────────────────────────────────────

    op.create_table(
        "user_organization",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_user_organization"),
    )

    op.create_table(
        "user_role",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "role_id", name="uq_user_role"),
    )

    op.create_table(
        "role_permission",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["role_id"], ["role.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["permission_id"], ["permission.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("role_id", "permission_id", name="uq_role_permission"),
    )

    # ── auth token tables ──────────────────────────────────────────────────────

    op.create_table(
        "password_reset_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )

    op.create_table(
        "refresh_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("jti", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_reason", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti"),
        sa.UniqueConstraint("token"),
    )
    op.create_index("ix_refresh_token_jti", "refresh_token", ["jti"])

    op.create_table(
        "api_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("token_hash", sa.String(), nullable=False),
        sa.Column("token_prefix", sa.String(), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=False, server_default="[]"),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_used_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token_hash"),
    )
    op.create_index(
        op.f("ix_api_token_token_hash"), "api_token", ["token_hash"], unique=True
    )
    op.create_index(op.f("ix_api_token_user_id"), "api_token", ["user_id"])
    op.create_index(
        op.f("ix_api_token_organization_id"), "api_token", ["organization_id"]
    )

    op.create_table(
        "invite_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_invite_token_email"), "invite_token", ["email"], unique=True
    )

    op.create_table(
        "email_verification_token",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=False),
        sa.Column("terms_accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        op.f("ix_email_verification_token_email"),
        "email_verification_token",
        ["email"],
        unique=True,
    )

    op.create_table(
        "waitlist_entry",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(
        op.f("ix_waitlist_entry_email"),
        "waitlist_entry",
        ["email"],
        unique=True,
    )

    # ── billing tables ─────────────────────────────────────────────────────────

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
        sa.UniqueConstraint(
            "external_product_id", name="uq_billing_plan_external_product_id"
        ),
    )
    op.create_index("ix_billing_plan_name", "billing_plan", ["name"])
    op.create_index(
        "ix_billing_plan_external_product_id", "billing_plan", ["external_product_id"]
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
        sa.UniqueConstraint(
            "external_price_id", name="uq_billing_plan_price_external_price_id"
        ),
    )
    op.create_index("ix_billing_plan_price_plan_id", "billing_plan_price", ["plan_id"])
    op.create_index(
        "ix_billing_plan_price_external_price_id",
        "billing_plan_price",
        ["external_price_id"],
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
        sa.UniqueConstraint(
            "external_subscription_id",
            name="uq_billing_subscription_external_subscription_id",
        ),
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
        sa.Column("external_event_id", sa.String(), nullable=False, unique=True),
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
    op.create_index("ix_billing_plan_setting_plan_id", "billing_plan_setting", ["plan_id"])
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
            "organization_id", "metric", "period_start",
            name="uq_billing_plan_usage",
        ),
    )
    op.create_index(
        "ix_billing_plan_usage_organization_id",
        "billing_plan_usage",
        ["organization_id"],
    )

    # ── seed all permissions ───────────────────────────────────────────────────

    now = datetime.now(UTC)
    op.bulk_insert(
        _permission_table,
        [
            {
                "name": p.value,
                "description": PERMISSION_DESCRIPTIONS[p],
                "created_at": now,
                "updated_at": now,
            }
            for p in ALL_PERMISSIONS
        ],
    )

    # ── audit log ──────────────────────────────────────────────────────────────

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization.id"],
            name="fk_audit_log_organization_id_organization",
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["user.id"],
            name="fk_audit_log_user_id_user",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_log_organization_id", "audit_log", ["organization_id"])
    op.create_index("ix_audit_log_user_id", "audit_log", ["user_id"])
    op.create_index("ix_audit_log_created_at", "audit_log", ["created_at"])
    op.create_index(
        "ix_audit_log_org_action",
        "audit_log",
        ["organization_id", "action"],
    )

    # ── notifications ──────────────────────────────────────────────────────────
    op.create_table(
        "notification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["organization_id"], ["organization.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_user_id", "notification", ["user_id"])
    op.create_index("ix_notification_organization_id", "notification", ["organization_id"])
    op.create_index("ix_notification_created_at", "notification", ["created_at"])

    # ── background worker runs ─────────────────────────────────────────────────
    op.create_table(
        "worker_run",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("worker_type", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("items_processed", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("changes_detected", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error_count", sa.Integer(), nullable=False, server_default="0"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_worker_run_started_at", "worker_run", ["started_at"])
    op.create_index("ix_worker_run_worker_type", "worker_run", ["worker_type"])

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

    # ── start auto-increment ids from SEQUENCE_START ──────────────────────────
    if op.get_bind().dialect.name == "postgresql":
        for _table in ("organization", "user"):
            op.execute(f"ALTER SEQUENCE {_table}_id_seq RESTART WITH {SEQUENCE_START}")


def downgrade() -> None:
    op.drop_index("ix_worker_run_worker_type", table_name="worker_run")
    op.drop_index("ix_worker_run_started_at", table_name="worker_run")
    op.drop_table("worker_run")

    op.drop_index("ix_notification_created_at", table_name="notification")
    op.drop_index("ix_notification_organization_id", table_name="notification")
    op.drop_index("ix_notification_user_id", table_name="notification")
    op.drop_table("notification")
    op.drop_index("ix_audit_log_org_action", table_name="audit_log")
    op.drop_index("ix_audit_log_created_at", table_name="audit_log")
    op.drop_index("ix_audit_log_user_id", table_name="audit_log")
    op.drop_index("ix_audit_log_organization_id", table_name="audit_log")
    op.drop_table("audit_log")

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

    op.drop_index(op.f("ix_waitlist_entry_email"), table_name="waitlist_entry")
    op.drop_table("waitlist_entry")

    op.drop_index(
        op.f("ix_email_verification_token_email"),
        table_name="email_verification_token",
    )
    op.drop_table("email_verification_token")

    op.drop_index(op.f("ix_invite_token_email"), table_name="invite_token")
    op.drop_table("invite_token")

    op.drop_index(op.f("ix_api_token_organization_id"), table_name="api_token")
    op.drop_index(op.f("ix_api_token_user_id"), table_name="api_token")
    op.drop_index(op.f("ix_api_token_token_hash"), table_name="api_token")
    op.drop_table("api_token")

    op.drop_table("refresh_token")
    op.drop_table("password_reset_token")
    op.drop_table("role_permission")
    op.drop_table("user_role")
    op.drop_table("user_organization")

    op.drop_index(op.f("ix_role_name"), table_name="role")
    op.drop_table("role")

    op.drop_index(op.f("ix_user_name"), table_name="user")
    op.drop_table("user")

    op.drop_index(op.f("ix_permission_name"), table_name="permission")
    op.drop_table("permission")

    op.drop_index("ix_organization_external_customer_id", table_name="organization")
    op.drop_index(op.f("ix_organization_name"), table_name="organization")
    op.drop_table("organization")
