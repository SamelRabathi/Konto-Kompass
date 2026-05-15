from .base import Position, Balance


class ManualConnector:
    def fetch_positions(self, external_ref: str, token_blob: str | None):
        return []

    def fetch_balances(self, external_ref: str, token_blob: str | None):
        return []
