import os
from typing import List

import httpx

from .base import Position, Balance


class GoCardlessConnector:
    def __init__(self):
        self.secret_id = os.environ.get("GOCARDLESS_SECRET_ID", "")
        self.secret_key = os.environ.get("GOCARDLESS_SECRET_KEY", "")
        self.base_url = os.environ.get(
            "GOCARDLESS_BASE_URL",
            "https://bankaccountdata.gocardless.com/api/v2",
        )

    def _headers(self, access_token: str) -> dict:
        return {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}

    def _get_access_token(self) -> str | None:
        if not self.secret_id or not self.secret_key:
            return None
        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(
                    f"{self.base_url}/token/new/",
                    json={"secret_id": self.secret_id, "secret_key": self.secret_key},
                )
                resp.raise_for_status()
                return resp.json().get("access")
        except httpx.HTTPError:
            return None

    def fetch_positions(self, external_ref: str, token_blob: str | None) -> List[Position]:
        return []

    def fetch_balances(self, external_ref: str, token_blob: str | None) -> List[Balance]:
        account_id = external_ref
        if not account_id:
            return []

        token = self._get_access_token()
        if not token:
            return []

        try:
            with httpx.Client(timeout=30.0) as client:
                resp = client.get(
                    f"{self.base_url}/accounts/{account_id}/balances/",
                    headers=self._headers(token),
                )
                resp.raise_for_status()
                data = resp.json()
        except httpx.HTTPError:
            return []

        balances: list[Balance] = []
        for item in data.get("balances", []):
            amount = item.get("balanceAmount", {}).get("amount", "0")
            try:
                val = float(amount)
            except (TypeError, ValueError):
                val = 0.0
            balances.append(
                Balance(
                    account_name=item.get("referenceDate") or account_id,
                    amount_eur=val,
                    external_ref=account_id,
                )
            )
        return balances
