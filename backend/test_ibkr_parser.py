from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree

import pytest

from investments.ibkr_parser import parse_ibkr_xml


@pytest.mark.parametrize("fx_rate", ["1", "0.923456789012"])
def test_preserves_fx_rate_precision(fx_rate: str) -> None:
    source = BytesIO(
        '<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
        'assetCategory="STK" quantity="1" tradePrice="10" '
        f'fxRateToBase="{fx_rate}" buySell="BUY" netCash="-11" '
        'dateTime="20260929;120000" symbol="TEST" currency="USD" />'
        "</FlexQueryResponse>".encode()
    )

    activities = parse_ibkr_xml(source)

    assert len(activities) == 1
    assert isinstance(activities[0]["fx_rate"], Decimal)
    assert activities[0]["fx_rate"] == Decimal(fx_rate)


@pytest.mark.parametrize("fx_rate", ["0", "-1", "NaN", "Infinity", "-Infinity"])
def test_rejects_invalid_fx_rate(fx_rate: str) -> None:
    source = BytesIO(
        '<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
        'assetCategory="STK" quantity="1" tradePrice="10" '
        f'fxRateToBase="{fx_rate}" buySell="BUY" netCash="-11" '
        'dateTime="20260929;120000" symbol="TEST" currency="USD" />'
        "</FlexQueryResponse>".encode()
    )

    with pytest.raises(ValueError, match="Invalid FX rate"):
        parse_ibkr_xml(source)


@pytest.mark.parametrize(
    ("side", "quantity", "net_cash"),
    [("BUY", "2.5", "-26"), ("SELL", "-2.5", "24")],
)
def test_normalizes_trade_quantity(side: str, quantity: str, net_cash: str) -> None:
    source = BytesIO(
        '<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
        f'assetCategory="STK" quantity="{quantity}" tradePrice="10" '
        f'fxRateToBase="1" buySell="{side}" netCash="{net_cash}" '
        'dateTime="20260929;120000" symbol="TEST" currency="USD" />'
        "</FlexQueryResponse>".encode()
    )

    activity = parse_ibkr_xml(source)[0]

    assert activity["activity_type"] == f"{side} - MARKET"
    assert activity["quantity"] == Decimal("2.5")
    assert activity["total_amount"] == Decimal("26" if side == "BUY" else "24")


@pytest.mark.parametrize(
    ("side", "quantity", "net_cash", "message"),
    [
        ("BUY", "-2", "-21", "Expected positive quantity for a purchase"),
        ("SELL", "2", "19", "Expected negative quantity for a sale"),
        ("BUY", "0", "-1", "Invalid quantity"),
        ("SELL", "0", "-1", "Invalid quantity"),
    ],
)
def test_rejects_incorrect_trade_quantity(
    side: str, quantity: str, net_cash: str, message: str
) -> None:
    source = BytesIO(
        '<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
        f'assetCategory="STK" quantity="{quantity}" tradePrice="10" '
        f'fxRateToBase="1" buySell="{side}" netCash="{net_cash}" '
        'dateTime="20260929;120000" symbol="TEST" currency="USD" />'
        "</FlexQueryResponse>".encode()
    )

    with pytest.raises(ValueError, match=message):
        parse_ibkr_xml(source)


@pytest.mark.parametrize("category", ["OPT", "FUT", "CASH", "", None])
def test_rejects_unsupported_or_missing_asset_category(category: str | None) -> None:
    category_attribute = "" if category is None else f'assetCategory="{category}"'
    source = BytesIO(
        '<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
        f'{category_attribute} quantity="1" tradePrice="10" '
        'fxRateToBase="1" buySell="BUY" netCash="-11" '
        'dateTime="20260929;120000" symbol="TEST" currency="USD" />'
        "</FlexQueryResponse>".encode()
    )

    with pytest.raises(ValueError, match="Unsupported IBKR asset category"):
        parse_ibkr_xml(source)


@pytest.mark.parametrize(
    ("ticker", "currency"),
    [(" TEST ", " USD "), ("X" * 20, "EUR"), ("BRK.B", "USD")],
)
def test_normalizes_valid_ticker_and_currency(ticker: str, currency: str) -> None:
    source = BytesIO(
        '<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
        'assetCategory="STK" quantity="1" tradePrice="10" '
        'fxRateToBase="1" buySell="BUY" netCash="-11" '
        f'dateTime="20260929;120000" symbol="{ticker}" currency="{currency}" />'
        "</FlexQueryResponse>".encode()
    )

    activity = parse_ibkr_xml(source)[0]

    assert activity["ticker"] == ticker.strip()
    assert activity["currency"] == currency.strip()


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("symbol", None, "Invalid ticker"),
        ("symbol", "", "Invalid ticker"),
        ("symbol", "   ", "Invalid ticker"),
        ("symbol", "X" * 21, "Invalid ticker"),
        ("currency", None, "Invalid currency"),
        ("currency", "", "Invalid currency"),
        ("currency", "   ", "Invalid currency"),
        ("currency", "US", "Invalid currency"),
        ("currency", "USDD", "Invalid currency"),
        ("currency", "usd", "Invalid currency"),
        ("currency", "U1D", "Invalid currency"),
        ("currency", "USÉ", "Invalid currency"),
    ],
)
def test_rejects_invalid_ticker_or_currency(
    field: str, value: str | None, message: str
) -> None:
    root = ElementTree.fromstring(
        '<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
        'assetCategory="STK" quantity="1" tradePrice="10" '
        'fxRateToBase="1" buySell="BUY" netCash="-11" '
        'dateTime="20260929;120000" symbol="TEST" currency="USD" />'
        "</FlexQueryResponse>"
    )
    if value is None:
        del root[0].attrib[field]
    else:
        root[0].attrib[field] = value
    source = BytesIO(ElementTree.tostring(root))

    with pytest.raises(ValueError, match=message):
        parse_ibkr_xml(source)
