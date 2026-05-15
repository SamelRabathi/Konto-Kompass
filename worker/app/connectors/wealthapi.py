import logging
import os
from typing import List

import httpx

from .base import Position, Balance

logger = logging.getLogger(__name__)


class WealthApiConnector:
    def __init__(self):
        self.api_key = os.environ.get("WEALTHAPI_KEY", "")
        self.base_url = os.environ.get("WEALTHAPI_BASE_URL", "https://api.wealthapi.eu")

    def fetch_positions(self, external_ref: str, token_blob: str | None) -> List[Position]:
        if not self.api_key:
            raise RuntimeError("WealthAPI: WEALTHAPI_KEY fehlt in .env.")
        if not (external_ref or "").strip():
            raise ValueError(
                "WealthAPI: external_ref fehlt. Das ist die Depot-ID aus dem WealthAPI-Dashboard/API, "
                "nicht die Kontonummer der Bank."
            )

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.base_url}/depots/{external_ref}/positions",
                headers={"X-API-KEY": self.api_key},
            )
            if not resp.is_success:
                logger.error(
                    "WealthAPI positions HTTP %s: %s",
                    resp.status_code,
                    (resp.text or "")[:500],
                )
            resp.raise_for_status()
            payload = resp.json()

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
        if not self.api_key:
            raise RuntimeError("WealthAPI: WEALTHAPI_KEY fehlt in .env.")
        if not (external_ref or "").strip():
            return []

        with httpx.Client(timeout=30.0) as client:
            resp = client.get(
                f"{self.base_url}/depots/{external_ref}",
                headers={"X-API-KEY": self.api_key},
            )
            if resp.status_code == 404:
                return []
            if not resp.is_success:
                logger.error(
                    "WealthAPI depot HTTP %s: %s",
                    resp.status_code,
                    (resp.text or "")[:500],
                )
            resp.raise_for_status()
            data = resp.json()

        cash = float(data.get("cash") or data.get("cashBalance") or 0)
        if cash == 0:
            return []
        return [Balance(account_name=f"Depot {external_ref}", amount_eur=cash, external_ref=external_ref)]
