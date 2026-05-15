import os
from typing import List

import httpx

from .base import Position, Balance


class WealthApiConnector:
    def __init__(self):
        self.api_key = os.environ.get("WEALTHAPI_KEY", "")
        self.base_url = os.environ.get("WEALTHAPI_BASE_URL", "https://api.wealthapi.eu")

    def fetch_positions(self, external_ref: str, token_blob: str | None) -> List[Position]:
        if not self.api_key or not external_ref:
            return []

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{self.base_url}/depots/{external_ref}/positions",
                    headers={"X-API-KEY": self.api_key},
                )
                if resp.status_code == 404:
                    return []
                resp.raise_for_status()
                payload = resp.json()
        except httpx.HTTPError:
            return []

        positions: list[Position] = []
        items = payload if isinstance(payload, list) else payload.get("positions", [])
        for item in items:
            asset_type = (item.get("assetType") or item.get("type") or "stock").lower()
            if "etf" in asset_type:
                asset_type = "etf"
            positions.append(
                Position(
                    asset_type=asset_type,
                    symbol=str(item.get("symbol") or item.get("name") or "UNKNOWN")[:50],
                    isin=item.get("isin"),
                    quantity=float(item.get("quantity") or 0),
                    market_value_eur=float(item.get("marketValue") or item.get("market_value_eur") or 0),
                )
            )
        return positions

    def fetch_balances(self, external_ref: str, token_blob: str | None) -> List[Balance]:
        if not self.api_key or not external_ref:
            return []
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{self.base_url}/depots/{external_ref}",
                    headers={"X-API-KEY": self.api_key},
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError:
            return []

        cash = float(data.get("cash") or data.get("cashBalance") or 0)
        if cash == 0:
            return []
        return [Balance(account_name=f"Depot {external_ref}", amount_eur=cash, external_ref=external_ref)]
