from datetime import datetime

from sqlalchemy.orm import Session

from konto_models import FinancialArea, Account, Holding, BalanceSnapshot, Connection
from konto_connectors import parse_holdings_csv, parse_balance_csv
from .crypto import encrypt_token_blob


def _get_area(db: Session, tenant_id: int, slug: str) -> FinancialArea:
    area = (
        db.query(FinancialArea)
        .filter(FinancialArea.tenant_id == tenant_id, FinancialArea.slug == slug)
        .first()
    )
    if not area:
        raise ValueError(f"Bereich '{slug}' fehlt")
    return area


def import_holdings_csv(
    db: Session,
    tenant_id: int,
    csv_content: str,
    account_name: str,
    provider_label: str = "csv_import",
) -> dict:
    investments = _get_area(db, tenant_id, "investments")
    conn = Connection(
        tenant_id=tenant_id,
        provider="csv_import",
        label=provider_label,
        token_blob=encrypt_token_blob({"csv_content": csv_content, "kind": "holdings"}),
    )
    db.add(conn)
    db.flush()

    account = Account(
        tenant_id=tenant_id,
        area_id=investments.id,
        connection_id=conn.id,
        provider="csv_import",
        name=account_name,
        is_manual=True,
    )
    db.add(account)
    db.flush()

    positions = parse_holdings_csv(csv_content)
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
    db.commit()
    return {
        "account_id": account.id,
        "connection_id": conn.id,
        "positions_imported": len(positions),
    }


def import_balance_csv(
    db: Session,
    tenant_id: int,
    csv_content: str,
    default_account_name: str,
) -> dict:
    liquidity = _get_area(db, tenant_id, "liquidity")
    balances = parse_balance_csv(csv_content)
    if not balances:
        raise ValueError(
            "Keine Salden erkannt. CSV braucht Spalten wie Saldo, Kontostand, Betrag oder Amount."
        )

    account_ids: list[int] = []
    for entry in balances:
        name = entry.account_label if entry.account_label != "Import" else default_account_name
        account = Account(
            tenant_id=tenant_id,
            area_id=liquidity.id,
            provider="csv_import",
            name=name,
            is_manual=True,
        )
        db.add(account)
        db.flush()
        db.add(
            BalanceSnapshot(
                account_id=account.id,
                amount_eur=entry.amount_eur,
                ts=datetime.utcnow(),
            )
        )
        account_ids.append(account.id)

    db.commit()
    return {"accounts_updated": len(account_ids), "account_ids": account_ids}
