from sqlalchemy.orm import Session

from konto_models import (
    Tenant,
    FinancialArea,
    Account,
    Holding,
    BalanceSnapshot,
    Liability,
    DEFAULT_AREAS,
)


def seed_default_areas(db: Session, tenant_id: int) -> None:
    existing = {a.slug for a in db.query(FinancialArea).filter(FinancialArea.tenant_id == tenant_id).all()}
    for area in DEFAULT_AREAS:
        if area["slug"] not in existing:
            db.add(
                FinancialArea(
                    tenant_id=tenant_id,
                    slug=area["slug"],
                    label=area["label"],
                    sort_order=area["sort_order"],
                )
            )
    db.flush()


def get_area_by_slug(db: Session, tenant_id: int, slug: str) -> FinancialArea | None:
    return (
        db.query(FinancialArea)
        .filter(FinancialArea.tenant_id == tenant_id, FinancialArea.slug == slug)
        .first()
    )


def compute_tenant_overview(db: Session, tenant_id: int) -> dict:
    areas = db.query(FinancialArea).filter(FinancialArea.tenant_id == tenant_id).all()
    area_slug_by_id = {a.id: a.slug for a in areas}
    liquidity = 0.0
    investments = 0.0

    accounts = db.query(Account).filter(Account.tenant_id == tenant_id).all()
    for account in accounts:
        area_slug = area_slug_by_id.get(account.area_id, "liquidity")
        latest_balance = (
            db.query(BalanceSnapshot)
            .filter(BalanceSnapshot.account_id == account.id)
            .order_by(BalanceSnapshot.ts.desc())
            .first()
        )
        balance_val = float(latest_balance.amount_eur) if latest_balance else 0.0
        holdings_val = sum(
            float(h.market_value_eur)
            for h in db.query(Holding).filter(Holding.account_id == account.id).all()
        )

        if area_slug == "investments":
            investments += holdings_val + balance_val
        else:
            liquidity += balance_val + (holdings_val if area_slug != "liabilities" else 0.0)

    liabilities_total = sum(
        float(l.remaining_eur) for l in db.query(Liability).filter(Liability.tenant_id == tenant_id).all()
    )
    net_worth = liquidity + investments - liabilities_total

    return {
        "assets_liquidity_eur": round(liquidity, 2),
        "assets_investments_eur": round(investments, 2),
        "liabilities_total_eur": round(liabilities_total, 2),
        "net_worth_eur": round(net_worth, 2),
        "areas": [{"slug": a.slug, "label": a.label, "sort_order": a.sort_order} for a in sorted(areas, key=lambda x: x.sort_order)],
    }
