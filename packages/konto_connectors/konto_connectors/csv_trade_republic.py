import csv
import io
from typing import List

from .base import Position


def _parse_float(value: str) -> float:
    cleaned = (value or "").strip().replace("€", "").replace(" ", "").replace(".", "").replace(",", ".")
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_trade_republic_csv(content: str) -> List[Position]:
    """Parse Trade Republic portfolio/activity CSV exports (flexible headers)."""
    reader = csv.DictReader(io.StringIO(content))
    positions: list[Position] = []

    for row in reader:
        if not row:
            continue
        normalized = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}

        symbol = (
            normalized.get("instrument")
            or normalized.get("name")
            or normalized.get("wertpapier")
            or normalized.get("symbol")
            or "UNKNOWN"
        )
        isin = normalized.get("isin") or normalized.get("isin/code") or None
        qty = _parse_float(
            normalized.get("quantity")
            or normalized.get("stück")
            or normalized.get("stueck")
            or normalized.get("amount")
            or "0"
        )
        value = _parse_float(
            normalized.get("market value")
            or normalized.get("marktwert")
            or normalized.get("value")
            or normalized.get("wert")
            or normalized.get("kurswert")
            or "0"
        )
        asset_type = normalized.get("type") or normalized.get("asset type") or "stock"
        if "etf" in asset_type.lower():
            asset_type = "etf"
        elif "fund" in asset_type.lower():
            asset_type = "fund"
        else:
            asset_type = "stock"

        if value == 0 and qty == 0:
            continue

        positions.append(
            Position(
                asset_type=asset_type,
                symbol=symbol[:50],
                isin=isin[:20] if isin else None,
                quantity=qty,
                market_value_eur=value if value else qty,
            )
        )
    return positions
