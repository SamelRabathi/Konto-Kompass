from sqlalchemy import String, DateTime, ForeignKey, Numeric, Boolean, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .db import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)

class Connection(Base):
    __tablename__ = "connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))  # "wealthapi" | "gocardless"
    label: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="active")  # active|needs_reauth|disabled
    external_ref: Mapped[str] = mapped_column(String(200), nullable=True)  # aggregator connection id
    token_blob: Mapped[str] = mapped_column(Text, nullable=True)  # encrypted JSON (optional)

class DailySnapshot(Base):
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
