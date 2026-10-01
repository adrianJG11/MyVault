from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree

import pytest

from investments import ibkr_parser
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


def _report_with_trades(*overrides: dict[str, str]) -> bytes:
    root = ElementTree.Element("FlexQueryResponse")
    for changes in overrides:
        attributes = {
            "accountId": "TEST_ACCOUNT",
            "tradeID": "123",
            "assetCategory": "STK",
            "quantity": "1",
            "tradePrice": "10",
            "fxRateToBase": "1",
            "buySell": "BUY",
            "netCash": "-11",
            "dateTime": "20260929;120000",
            "symbol": "TEST",
            "currency": "USD",
        }
        ElementTree.SubElement(root, "Trade", attributes | changes)
    return ElementTree.tostring(root)


def test_same_report_produces_stable_fingerprints() -> None:
    report = _report_with_trades({})
    assert parse_ibkr_xml(BytesIO(report)) == parse_ibkr_xml(BytesIO(report))


def test_distinct_identical_executions_have_distinct_fingerprints() -> None:
    activities = parse_ibkr_xml(BytesIO(_report_with_trades({}, {"tradeID": "124"})))
    assert activities[0]["import_fingerprint"] != activities[1]["import_fingerprint"]


@pytest.mark.parametrize("field", ["accountId", "tradeID"])
def test_rejects_missing_trade_identity(field: str) -> None:
    with pytest.raises(ValueError, match="Missing IBKR trade identity"):
        parse_ibkr_xml(BytesIO(_report_with_trades({field: " "})))


def test_rejects_reports_combining_broker_accounts() -> None:
    report = _report_with_trades({}, {"accountId": "OTHER_ACCOUNT", "tradeID": "124"})
    with pytest.raises(ValueError, match="Expected one IBKR account"):
        parse_ibkr_xml(BytesIO(report))


@pytest.mark.parametrize("encoding", ["utf-8", "utf-16"])
def test_rejects_xml_document_types(encoding: str) -> None:
    report = '<!DOCTYPE FlexQueryResponse [<!ENTITY value "TEST">]><FlexQueryResponse/>'
    with pytest.raises(ValueError, match="document type"):
        parse_ibkr_xml(BytesIO(report.encode(encoding)))


def test_rejects_oversized_reports(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ibkr_parser, "MAX_IBKR_REPORT_BYTES", 64)
    with pytest.raises(ValueError, match="exceeds 10 MB"):
        parse_ibkr_xml(BytesIO(b" " * 65))


def test_sale_preserves_negative_proceeds_after_fees() -> None:
    report = _report_with_trades({"buySell": "SELL", "quantity": "-1", "netCash": "-1"})
    assert parse_ibkr_xml(BytesIO(report))[0]["total_amount"] == Decimal(-1)


def test_rejects_unknown_xml_encoding() -> None:
    report = b'<?xml version="1.0" encoding="UNKNOWN"?><FlexQueryResponse/>'
    with pytest.raises(ValueError, match="Invalid IBKR report"):
        parse_ibkr_xml(BytesIO(report))


@pytest.mark.parametrize(
    "changes",
    [
        {"netCash": "-1e1000000"},
        {"buySell": "SELL", "quantity": "-1e1000000"},
    ],
)
def test_decimal_overflow_raises_value_error(changes: dict[str, str]) -> None:
    with pytest.raises(ValueError, match="Invalid IBKR report"):
        parse_ibkr_xml(BytesIO(_report_with_trades(changes)))


@pytest.mark.parametrize(
    "report",
    [
        pytest.param(b"<FlexQueryResponse>", id="malformed_xml"),
        pytest.param(
            b'<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
            b'assetCategory="STK" tradePrice="10" fxRateToBase="1" '
            b'buySell="BUY" netCash="-11" dateTime="20260929;120000" '
            b'symbol="TEST" currency="USD" /></FlexQueryResponse>',
            id="missing_quantity",
        ),
        pytest.param(
            b'<FlexQueryResponse><Trade accountId="TEST_ACCOUNT" tradeID="123" '
            b'assetCategory="STK" quantity="abc" tradePrice="10" fxRateToBase="1" '
            b'buySell="BUY" netCash="-11" dateTime="20260929;120000" '
            b'symbol="TEST" currency="USD" /></FlexQueryResponse>',
            id="non_numeric_quantity",
        ),
    ],
)
def test_invalid_report_input_raises_value_error(report: bytes) -> None:
    with pytest.raises(ValueError, match="Invalid IBKR report"):
        parse_ibkr_xml(BytesIO(report))


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
