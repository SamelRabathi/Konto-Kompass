from konto_connectors import parse_trade_republic_csv, Position, Balance

from ..crypto import decrypt_token_blob
from .base import Connector


class CsvTradeRepublicConnector:
    def fetch_positions(self, external_ref: str, token_blob: str | None):
        data = decrypt_token_blob(token_blob)
        if not data:
            return []
        csv_content = data.get("csv_content") if isinstance(data, dict) else str(data)
        return parse_trade_republic_csv(csv_content)

    def fetch_balances(self, external_ref: str, token_blob: str | None):
        return []
