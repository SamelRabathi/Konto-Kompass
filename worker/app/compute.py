from typing import List, Dict
from .connectors.base import Position, Balance

def compute_totals(positions: List[Position], balances: List[Balance]) -> Dict[str, float]:
    totals = {"eos": 0.0, "stock": 0.0, "cash": 0.0, "total": 0.0}

    for p in positions:
        if p.asset_type in ("eos", "stock"):
            totals[p.asset_type] += float(p.market_value_eur)

    totals["cash"] += sum(float(b.amount_eur) for b in balances)
    totals["total"] = totals["eos"] + totals["stock"] + totals["cash"]
    return totals
