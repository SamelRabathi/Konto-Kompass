import os
from .base import Connector, Position, Balance

class GoCardlessConnector(Connector):
    def __init__(self):
        self.secret_id = os.environ["GOCARDLESS_SECRET_ID"]
        self.secret_key = os.environ["GOCARDLESS_SECRET_KEY"]

    def fetch_positions(self, external_ref: str, token_blob: str | None):
        # Bank AIS liefert typischerweise keine Depotpositionen
        return []

    def fetch_balances(self, external_ref: str, token_blob: str | None):
        # TODO: call GoCardless Bank Account Data balances endpoint
        return []
