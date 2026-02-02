import os
from .base import Connector, Position, Balance

class WealthApiConnector(Connector):
    def __init__(self):
        self.api_key = os.environ["WEALTHAPI_KEY"]

    def fetch_positions(self, external_ref: str, token_blob: str | None):
        # TODO: call wealthAPI holdings endpoint
        # return list[Position]
        return []

    def fetch_balances(self, external_ref: str, token_blob: str | None):
        # TODO: call wealthAPI cash/balances endpoint
        return []
