from datetime import date
from decimal import Decimal
from io import BytesIO
from xml.etree import ElementTree

import pytest

from investments.ibkr_parser import parse_ibkr_report


def _report(*overrides: dict[str, str | None]) -> bytes:
    root = ElementTree.Element("FlexQueryResponse")
    statement = ElementTree.SubElement(root, "FlexStatement", accountId="TEST_ACCOUNT")
    positions = ElementTree.SubElement(statement, "OpenPositions")
    for changes in overrides:
        attributes = {
            "accountId": "TEST_ACCOUNT",
            "assetCategory": "STK",
            "levelOfDetail": "SUMMARY",
            "symbol": "VWCE",
            "currency": "EUR",
            "markPrice": "123.45678901",
            "reportDate": "20260930",
        } | changes
        ElementTree.SubElement(
            positions,
            "OpenPosition",
            {key: value for key, value in attributes.items() if value is not None},
        )
    return ElementTree.tostring(root)


def test_parses_closing_prices_without_trade_history() -> None:
    activities, prices = parse_ibkr_report(BytesIO(_report({}, {"symbol": "SXRV"})))

    assert activities == []
    assert [price.ticker for price in prices] == ["VWCE", "SXRV"]
    assert prices[0].currency == "EUR"
    assert prices[0].price == Decimal("123.45678901")
    assert prices[0].as_of_date == date(2026, 9, 30)


@pytest.mark.parametrize(
    "changes",
    [{"markPrice": value} for value in (None, "", "abc", "0", "-1", "NaN", "Infinity")]
    + [
        {"reportDate": None},
        {"reportDate": "20260230"},
        {"reportDate": "99991231"},
        {"accountId": "OTHER_ACCOUNT"},
        {"accountId": ""},
        {"assetCategory": "OPT"},
        {"levelOfDetail": "LOT"},
        {"levelOfDetail": None},
        {"symbol": ""},
        {"symbol": "X" * 21},
        {"currency": "usd"},
        {"currency": "U1D"},
    ],
)
def test_rejects_invalid_position_prices(changes: dict[str, str | None]) -> None:
    with pytest.raises(ValueError):
        parse_ibkr_report(BytesIO(_report(changes)))


@pytest.mark.parametrize("reverse", [False, True])
def test_selects_latest_report_price_independent_of_row_order(reverse: bool) -> None:
    entries = [
        {"reportDate": "20260929", "markPrice": "100"},
        {"reportDate": "20260930", "markPrice": "110"},
    ]
    if reverse:
        entries.reverse()
    _, prices = parse_ibkr_report(BytesIO(_report(*entries)))

    assert len(prices) == 1
    assert prices[0].price == Decimal(110)
    assert prices[0].as_of_date == date(2026, 9, 30)


@pytest.mark.parametrize("changes", [{"markPrice": "999"}, {"currency": "USD"}])
def test_rejects_conflicting_prices_for_same_ticker(changes: dict[str, str]) -> None:
    with pytest.raises(ValueError):
        parse_ibkr_report(BytesIO(_report({}, changes)))
