from datetime import datetime

from sqlalchemy import (
    String,
    DateTime,
    ForeignKey,
    Numeric,
    Boolean,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base

DEFAULT_AREAS = [
    {"slug": "liquidity", "label": "Guthaben", "sort_order": 1},
    {"slug": "investments", "label": "Investments", "sort_order": 2},
    {"slug": "liabilities", "label": "Schulden", "sort_order": 3},
]


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)
    threshold_total_eur: Mapped[float] = mapped_column(Numeric(18, 2), default=25000.0)

    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="tenant")
    areas: Mapped[list["FinancialArea"]] = relationship(back_populates="tenant")
    accounts: Mapped[list["Account"]] = relationship(back_populates="tenant")
    connections: Mapped[list["Connection"]] = relationship(back_populates="tenant")
    liabilities: Mapped[list["Liability"]] = relationship(back_populates="tenant")


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    memberships: Mapped[list["TenantMembership"]] = relationship(back_populates="user")


class TenantMembership(Base):
    __tablename__ = "tenant_memberships"
    __table_args__ = (UniqueConstraint("user_id", "tenant_id", name="uq_user_tenant"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    role: Mapped[str] = mapped_column(String(20), default="owner")  # owner|member|viewer

    user: Mapped["User"] = relationship(back_populates="memberships")
    tenant: Mapped["Tenant"] = relationship(back_populates="memberships")


class FinancialArea(Base):
    __tablename__ = "financial_areas"
    __table_args__ = (UniqueConstraint("tenant_id", "slug", name="uq_tenant_area_slug"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    slug: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(120))
    sort_order: Mapped[int] = mapped_column(default=0)

    tenant: Mapped["Tenant"] = relationship(back_populates="areas")
    accounts: Mapped[list["Account"]] = relationship(back_populates="area")


class Connection(Base):
    __tablename__ = "connections"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="active")
    external_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)
    token_blob: Mapped[str | None] = mapped_column(Text, nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="connections")
    accounts: Mapped[list["Account"]] = relationship(back_populates="connection")


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("financial_areas.id"), index=True)
    connection_id: Mapped[int | None] = mapped_column(ForeignKey("connections.id"), nullable=True)
    provider: Mapped[str] = mapped_column(String(50), default="manual")
    name: Mapped[str] = mapped_column(String(120))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    is_manual: Mapped[bool] = mapped_column(Boolean, default=True)
    external_ref: Mapped[str | None] = mapped_column(String(200), nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="accounts")
    area: Mapped["FinancialArea"] = relationship(back_populates="accounts")
    connection: Mapped["Connection | None"] = relationship(back_populates="accounts")
    holdings: Mapped[list["Holding"]] = relationship(back_populates="account")
    balance_snapshots: Mapped[list["BalanceSnapshot"]] = relationship(back_populates="account")


class Holding(Base):
    __tablename__ = "holdings"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    asset_type: Mapped[str] = mapped_column(String(30))
    symbol: Mapped[str] = mapped_column(String(50))
    isin: Mapped[str | None] = mapped_column(String(20), nullable=True)
    quantity: Mapped[float] = mapped_column(Numeric(18, 6))
    market_value_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    as_of: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    account: Mapped["Account"] = relationship(back_populates="holdings")


class BalanceSnapshot(Base):
    __tablename__ = "balance_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)
    amount_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    account: Mapped["Account"] = relationship(back_populates="balance_snapshots")


class Liability(Base):
    __tablename__ = "liabilities"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    label: Mapped[str] = mapped_column(String(120))
    liability_type: Mapped[str] = mapped_column(String(30))
    provider: Mapped[str | None] = mapped_column(String(50), nullable=True)
    principal_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    remaining_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    interest_rate: Mapped[float | None] = mapped_column(Numeric(6, 3), nullable=True)
    monthly_payment_eur: Mapped[float | None] = mapped_column(Numeric(18, 2), nullable=True)
    due_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    tenant: Mapped["Tenant"] = relationship(back_populates="liabilities")


class NetWorthSnapshot(Base):
    __tablename__ = "net_worth_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    assets_liquidity_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    assets_investments_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    liabilities_total_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    net_worth_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    eos_eur: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    stocks_eur: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    cash_eur: Mapped[float] = mapped_column(Numeric(18, 2), default=0)
    threshold_total_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    threshold_hit: Mapped[bool] = mapped_column(Boolean, default=False)


class DailySnapshot(Base):
    """Legacy snapshot table kept for backward compatibility."""

    __tablename__ = "daily_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    total_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    eos_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    stocks_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    cash_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    threshold_total_eur: Mapped[float] = mapped_column(Numeric(18, 2))
    threshold_hit: Mapped[bool] = mapped_column(Boolean, default=False)
