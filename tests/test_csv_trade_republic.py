from konto_connectors import parse_trade_republic_csv


def test_parse_trade_republic_csv():
    content = "Instrument,ISIN,Quantity,Market Value\nApple,US0378331005,2,300\n"
    positions = parse_trade_republic_csv(content)
    assert len(positions) == 1
    assert positions[0].symbol == "Apple"
    assert positions[0].isin == "US0378331005"
    assert positions[0].quantity == 2
    assert positions[0].market_value_eur == 300
