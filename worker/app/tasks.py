import os
from celery import shared_task
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Reuse API models quickly (in real project, move models to shared package)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, DateTime, ForeignKey, Numeric, Boolean, Text

DATABASE_URL = os.environ["DATABASE_URL"]
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase): pass

class Tenant(Base):
    __tablename__ = "tenants"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True)

class Connection(Base):
    __tablename__ = "connections"
    id: Mapped[int] = mapped_column(primary_key=True)
    tenant_id: Mapped[int] = mapped_column(ForeignKey("tenants.id"), index=True)
    provider: Mapped[str] = mapped_column(String(50))
    label: Mapped[str] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(30), default="active")
    external_ref: Mapped[str] = mapped_column(String(200), nullable=True)
    token_blob: Mapped[str] = mapped_column(Text, nullable=True)

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

Base.metadata.create_all(bind=engine)

from .connectors.wealthapi import WealthApiConnector
from .connectors.gocardless import GoCardlessConnector
from .compute import compute_totals

def connector_for(provider: str):
    if provider == "wealthapi":
        return WealthApiConnector()
    if provider == "gocardless":
        return GoCardlessConnector()
    raise ValueError(f"Unknown provider: {provider}")

@shared_task(name="app.tasks.sync_all_tenants")
def sync_all_tenants():
    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        for t in tenants:
            sync_tenant.delay(t.id)
    finally:
        db.close()

@shared_task(name="app.tasks.sync_tenant")
def sync_tenant(tenant_id: int):
    db = SessionLocal()
    try:
        conns = db.query(Connection).filter(Connection.tenant_id == tenant_id, Connection.status == "active").all()

        positions = []
        balances = []

        for c in conns:
            conn = connector_for(c.provider)
            positions += conn.fetch_positions(c.external_ref or "", c.token_blob)
            balances += conn.fetch_balances(c.external_ref or "", c.token_blob)

        totals = compute_totals(positions, balances)

        # TODO: pro tenant in eigener Tabelle speichern (thresholds). Hier erstmal fixed.
        threshold_total_eur = 25000.0
        hit = totals["total"] >= threshold_total_eur

        snap = DailySnapshot(
            tenant_id=tenant_id,
            ts=datetime.utcnow(),
            total_eur=totals["total"],
            eos_eur=totals["eos"],
            stocks_eur=totals["stock"],
            cash_eur=totals["cash"],
            threshold_total_eur=threshold_total_eur,
            threshold_hit=hit,
        )
        db.add(snap)
        db.commit()
        return {"tenant_id": tenant_id, "totals": totals, "threshold_hit": hit}
    finally:
        db.close()
