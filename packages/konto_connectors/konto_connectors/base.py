from dataclasses import dataclass


@dataclass
class Position:
    asset_type: str
    symbol: str
    isin: str | None
    quantity: float
    market_value_eur: float


@dataclass
class Balance:
    account_name: str
    amount_eur: float
    external_ref: str | None = None
