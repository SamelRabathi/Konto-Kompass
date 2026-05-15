"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-05-15

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("threshold_total_eur", sa.Numeric(18, 2), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "tenant_memberships",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),
    )
    op.create_index("ix_tenant_memberships_user_id", "tenant_memberships", ["user_id"])
    op.create_index("ix_tenant_memberships_tenant_id", "tenant_memberships", ["tenant_id"])

    op.create_table(
        "financial_areas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "slug", name="uq_tenant_area_slug"),
    )
    op.create_index("ix_financial_areas_tenant_id", "financial_areas", ["tenant_id"])

    op.create_table(
        "connections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("status", sa.String(length=30), nullable=True),
        sa.Column("external_ref", sa.String(length=200), nullable=True),
        sa.Column("token_blob", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_connections_tenant_id", "connections", ["tenant_id"])

    op.create_table(
        "accounts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("area_id", sa.Integer(), nullable=False),
        sa.Column("connection_id", sa.Integer(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=True),
        sa.Column("is_manual", sa.Boolean(), nullable=True),
        sa.Column("external_ref", sa.String(length=200), nullable=True),
        sa.ForeignKeyConstraint(["area_id"], ["financial_areas.id"]),
        sa.ForeignKeyConstraint(["connection_id"], ["connections.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_accounts_tenant_id", "accounts", ["tenant_id"])
    op.create_index("ix_accounts_area_id", "accounts", ["area_id"])

    op.create_table(
        "holdings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("asset_type", sa.String(length=30), nullable=False),
        sa.Column("symbol", sa.String(length=50), nullable=False),
        sa.Column("isin", sa.String(length=20), nullable=True),
        sa.Column("quantity", sa.Numeric(18, 6), nullable=False),
        sa.Column("market_value_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("as_of", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_holdings_account_id", "holdings", ["account_id"])

    op.create_table(
        "balance_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("amount_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_balance_snapshots_account_id", "balance_snapshots", ["account_id"])
    op.create_index("ix_balance_snapshots_ts", "balance_snapshots", ["ts"])

    op.create_table(
        "liabilities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=120), nullable=False),
        sa.Column("liability_type", sa.String(length=30), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=True),
        sa.Column("principal_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("remaining_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("interest_rate", sa.Numeric(6, 3), nullable=True),
        sa.Column("monthly_payment_eur", sa.Numeric(18, 2), nullable=True),
        sa.Column("due_date", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_liabilities_tenant_id", "liabilities", ["tenant_id"])

    op.create_table(
        "net_worth_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=True),
        sa.Column("assets_liquidity_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("assets_investments_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("liabilities_total_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_worth_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("eos_eur", sa.Numeric(18, 2), nullable=True),
        sa.Column("stocks_eur", sa.Numeric(18, 2), nullable=True),
        sa.Column("cash_eur", sa.Numeric(18, 2), nullable=True),
        sa.Column("threshold_total_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("threshold_hit", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_net_worth_snapshots_tenant_id", "net_worth_snapshots", ["tenant_id"])
    op.create_index("ix_net_worth_snapshots_ts", "net_worth_snapshots", ["ts"])

    op.create_table(
        "daily_snapshots",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("ts", sa.DateTime(), nullable=True),
        sa.Column("total_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("eos_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("stocks_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("cash_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("threshold_total_eur", sa.Numeric(18, 2), nullable=False),
        sa.Column("threshold_hit", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_daily_snapshots_tenant_id", "daily_snapshots", ["tenant_id"])
    op.create_index("ix_daily_snapshots_ts", "daily_snapshots", ["ts"])


def downgrade() -> None:
    op.drop_table("daily_snapshots")
    op.drop_table("net_worth_snapshots")
    op.drop_table("liabilities")
    op.drop_table("balance_snapshots")
    op.drop_table("holdings")
    op.drop_table("accounts")
    op.drop_table("connections")
    op.drop_table("financial_areas")
    op.drop_table("tenant_memberships")
    op.drop_table("users")
    op.drop_table("tenants")
