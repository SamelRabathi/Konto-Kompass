import csv
import io
from dataclasses import dataclass
from typing import List

from .base import Position
from .csv_trade_republic import _parse_float, parse_trade_republic_csv


@dataclass
class ParsedBalance:
    account_label: str
    amount_eur: float


def parse_holdings_csv(content: str) -> List[Position]:
    """Depot/Portfolio-CSV (Trade Republic, viele Broker-Exporte mit ISIN + Marktwert)."""
    return parse_trade_republic_csv(content)


def parse_balance_csv(content: str) -> List[ParsedBalance]:
    """
    Giro-/Konto-CSV: eine oder mehrere Zeilen mit Saldo.
    Erkannte Spalten u. a.: Saldo, Kontostand, Balance, Betrag, Amount.
    """
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    if not rows:
        return []

    results: list[ParsedBalance] = []
    for row in rows:
        if not row:
            continue
        normalized = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}

        label = (
            normalized.get("konto")
            or normalized.get("account")
            or normalized.get("kontoname")
            or normalized.get("name")
            or normalized.get("iban")
            or "Import"
        )
        amount_raw = (
            normalized.get("saldo")
            or normalized.get("kontostand")
            or normalized.get("balance")
            or normalized.get("betrag")
            or normalized.get("amount")
            or normalized.get("wert")
            or normalized.get("buchungssaldo")
            or ""
        )
        amount = _parse_float(amount_raw)
        if amount == 0 and len(normalized) == 1:
            only_val = next(iter(normalized.values()), "")
            amount = _parse_float(only_val)
        if amount == 0:
            continue
        results.append(ParsedBalance(account_label=label[:120], amount_eur=amount))

    return results
