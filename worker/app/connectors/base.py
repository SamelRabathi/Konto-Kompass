from dataclasses import dataclass
from typing import List

@dataclass
class Position:
    asset_type: str   # "eos" | "stock" | "cash"
    symbol: str
    isin: str | None
    quantity: float
    market_value_eur: float

@dataclass
class Balance:
    account_name: str
    amount_eur: float

class Connector:
    def fetch_positions(self, external_ref: str, token_blob: str | None) -> List[Position]:
        raise NotImplementedError

    def fetch_balances(self, external_ref: str, token_blob: str | None) -> List[Balance]:
        raise NotImplementedError
