from konto_connectors import parse_holdings_csv, parse_balance_csv

from ..crypto import decrypt_token_blob


class CsvImportConnector:
    def fetch_positions(self, external_ref: str, token_blob: str | None):
        data = decrypt_token_blob(token_blob)
        if not data or not isinstance(data, dict):
            return []
        if data.get("kind") == "holdings" or "csv_content" in data:
            return parse_holdings_csv(data.get("csv_content", ""))
        return []

    def fetch_balances(self, external_ref: str, token_blob: str | None):
        return []
