from worker.app.compute import compute_totals, compute_net_worth
from konto_connectors import Position, Balance


def test_compute_totals():
    positions = [
        Position(asset_type="stock", symbol="AAPL", isin=None, quantity=1, market_value_eur=100),
        Position(asset_type="eos", symbol="EOS", isin=None, quantity=1, market_value_eur=50),
    ]
    balances = [Balance(account_name="Giro", amount_eur=200)]
    totals = compute_totals(positions, balances)
    assert totals["stock"] == 100
    assert totals["eos"] == 50
    assert totals["cash"] == 200
    assert totals["total"] == 350


def test_compute_net_worth():
    assert compute_net_worth(1000, 5000, 2000) == 4000
