from konto_connectors import parse_balance_csv, parse_holdings_csv


def test_parse_balance_csv():
    content = "Konto,Saldo\nDeutsche Bank Giro,1234.56\n"
    rows = parse_balance_csv(content)
    assert len(rows) == 1
    assert rows[0].account_label == "Deutsche Bank Giro"
    assert rows[0].amount_eur == 1234.56


def test_parse_holdings_csv():
    content = "Instrument,ISIN,Quantity,Market Value\nApple,US0378331005,2,300\n"
    positions = parse_holdings_csv(content)
    assert len(positions) == 1
    assert positions[0].symbol == "Apple"
