from datetime import datetime

from celery import shared_task
from konto_models import (
    Tenant,
    Connection,
    FinancialArea,
    Account,
    Holding,
    BalanceSnapshot,
    Liability,
    NetWorthSnapshot,
    DailySnapshot,
)

from .db import SessionLocal
from .compute import compute_totals, compute_net_worth
from .connectors.wealthapi import WealthApiConnector
from .connectors.gocardless import GoCardlessConnector
from .connectors.csv_trade_republic import CsvTradeRepublicConnector
from .connectors.manual import ManualConnector
from konto_connectors import Position, Balance


def connector_for(provider: str):
    if provider == "wealthapi":
        return WealthApiConnector()
    if provider == "gocardless":
        return GoCardlessConnector()
    if provider == "csv_trade_republic":
        return CsvTradeRepublicConnector()
    if provider in ("manual",):
        return ManualConnector()
    raise ValueError(f"Unknown provider: {provider}")


def _area_for_slug(db, tenant_id: int, slug: str) -> FinancialArea | None:
    return (
        db.query(FinancialArea)
        .filter(FinancialArea.tenant_id == tenant_id, FinancialArea.slug == slug)
        .first()
    )


def _upsert_account(
    db,
    tenant_id: int,
    area_id: int,
    connection_id: int,
    provider: str,
    name: str,
    external_ref: str | None,
) -> Account:
    account = (
        db.query(Account)
        .filter(
            Account.tenant_id == tenant_id,
            Account.connection_id == connection_id,
            Account.external_ref == external_ref,
        )
        .first()
    )
    if not account:
        account = Account(
            tenant_id=tenant_id,
            area_id=area_id,
            connection_id=connection_id,
            provider=provider,
            name=name,
            is_manual=False,
            external_ref=external_ref,
        )
        db.add(account)
        db.flush()
    return account


def _persist_connector_data(db, tenant_id: int, connection: Connection, positions: list[Position], balances: list[Balance]):
    investments_area = _area_for_slug(db, tenant_id, "investments")
    liquidity_area = _area_for_slug(db, tenant_id, "liquidity")
    if not investments_area or not liquidity_area:
        return

    if connection.provider == "gocardless":
        for bal in balances:
            account = _upsert_account(
                db,
                tenant_id,
                liquidity_area.id,
                connection.id,
                connection.provider,
                bal.account_name,
                bal.external_ref,
            )
            db.add(BalanceSnapshot(account_id=account.id, amount_eur=bal.amount_eur, ts=datetime.utcnow()))
    elif connection.provider in ("wealthapi", "csv_trade_republic"):
        account = _upsert_account(
            db,
            tenant_id,
            investments_area.id,
            connection.id,
            connection.provider,
            connection.label,
            connection.external_ref,
        )
        db.query(Holding).filter(Holding.account_id == account.id).delete()
        for pos in positions:
            db.add(
                Holding(
                    account_id=account.id,
                    asset_type=pos.asset_type,
                    symbol=pos.symbol,
                    isin=pos.isin,
                    quantity=pos.quantity,
                    market_value_eur=pos.market_value_eur,
                    as_of=datetime.utcnow(),
                )
            )
        for bal in balances:
            db.add(BalanceSnapshot(account_id=account.id, amount_eur=bal.amount_eur, ts=datetime.utcnow()))


def _aggregate_from_db(db, tenant_id: int) -> dict:
    areas = db.query(FinancialArea).filter(FinancialArea.tenant_id == tenant_id).all()
    slug_by_id = {a.id: a.slug for a in areas}
    liquidity = 0.0
    investments = 0.0
    eos = 0.0
    stocks = 0.0
    cash = 0.0

    accounts = db.query(Account).filter(Account.tenant_id == tenant_id).all()
    for account in accounts:
        slug = slug_by_id.get(account.area_id, "liquidity")
        latest = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id)
            .order_by(BalanceSnapshot.ts.desc())
            .first()
        )
        bal = float(latest.amount_eur) if latest else 0.0
        holdings_val = sum(float(h.market_value_eur) for h in db.query(Holding).filter(Holding.account_id == account.id))
        for h in db.query(Holding).filter(Holding.account_id == account.id):
            if h.asset_type == "eos":
                eos += float(h.market_value_eur)
            else:
                stocks += float(h.market_value_eur)

        cash += bal
        if slug == "investments":
            investments += holdings_val + bal
        else:
            liquidity += bal + holdings_val

    liabilities_total = sum(
        float(l.remaining_eur) for l in db.query(Liability).filter(Liability.tenant_id == tenant_id).all()
    )
    net_worth = compute_net_worth(liquidity, investments, liabilities_total)
    legacy = compute_totals([], [Balance(amount_eur=cash, account_name="")])
    legacy["eos"] = eos
    legacy["stock"] = stocks
    legacy["cash"] = cash
    legacy["total"] = net_worth + liabilities_total

    return {
        "liquidity": liquidity,
        "investments": investments,
        "liabilities_total": liabilities_total,
        "net_worth": net_worth,
        "legacy": legacy,
    }


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
        tenant = db.query(Tenant).filter(Tenant.id == tenant_id).first()
        if not tenant:
            return {"error": "tenant not found"}

        conns = db.query(Connection).filter(Connection.tenant_id == tenant_id, Connection.status == "active").all()
        for c in conns:
            try:
                conn_impl = connector_for(c.provider)
                positions = conn_impl.fetch_positions(c.external_ref or "", c.token_blob)
                balances = conn_impl.fetch_balances(c.external_ref or "", c.token_blob)
                _persist_connector_data(db, tenant_id, c, positions, balances)
            except Exception:
                c.status = "needs_reauth"
                db.add(c)

        agg = _aggregate_from_db(db, tenant_id)
        threshold = float(tenant.threshold_total_eur or 25000)
        hit = agg["net_worth"] >= threshold

        snap = NetWorthSnapshot(
            tenant_id=tenant_id,
            ts=datetime.utcnow(),
            assets_liquidity_eur=agg["liquidity"],
            assets_investments_eur=agg["investments"],
            liabilities_total_eur=agg["liabilities_total"],
            net_worth_eur=agg["net_worth"],
            eos_eur=agg["legacy"]["eos"],
            stocks_eur=agg["legacy"]["stock"],
            cash_eur=agg["legacy"]["cash"],
            threshold_total_eur=threshold,
            threshold_hit=hit,
        )
        db.add(snap)

        legacy_snap = DailySnapshot(
            tenant_id=tenant_id,
            ts=datetime.utcnow(),
            total_eur=agg["legacy"]["total"],
            eos_eur=agg["legacy"]["eos"],
            stocks_eur=agg["legacy"]["stock"],
            cash_eur=agg["legacy"]["cash"],
            threshold_total_eur=threshold,
            threshold_hit=hit,
        )
        db.add(legacy_snap)
        db.commit()
        return {"tenant_id": tenant_id, "net_worth": agg["net_worth"], "threshold_hit": hit}
    finally:
        db.close()
