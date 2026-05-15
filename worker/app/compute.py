from typing import Dict, List

from konto_connectors import Position, Balance


def compute_totals(positions: List[Position], balances: List[Balance]) -> Dict[str, float]:
    totals = {"eos": 0.0, "stock": 0.0, "cash": 0.0, "total": 0.0}

    for p in positions:
        if p.asset_type == "eos":
            totals["eos"] += float(p.market_value_eur)
        elif p.asset_type in ("stock", "etf", "fund", "crypto", "other"):
            totals["stock"] += float(p.market_value_eur)

    totals["cash"] += sum(float(b.amount_eur) for b in balances)
    totals["total"] = totals["eos"] + totals["stock"] + totals["cash"]
    return totals


def compute_net_worth(liquidity: float, investments: float, liabilities: float) -> float:
    return round(liquidity + investments - liabilities, 2)
