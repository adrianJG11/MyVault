from datetime import UTC, datetime
from decimal import Decimal
from io import BytesIO

import pytest

from revolut_investment_importer import parse_revolut_investment_csv

HEADERS = "Date,Ticker,Type,Quantity,Price per share,Total Amount,Currency,FX Rate\n"


def _csv_file(*rows: str) -> BytesIO:
    return BytesIO((HEADERS + "".join(f"{row}\n" for row in rows)).encode())


def test_parse_revolut_investment_csv_accepts_expected_headers() -> None:
    assert parse_revolut_investment_csv(_csv_file()) == []


def test_parse_revolut_investment_csv_normalizes_supported_activities() -> None:
    activities = parse_revolut_investment_csv(
        _csv_file(
            "2026-01-10T12:30:00Z,FAKE,BUY - MARKET,0.5,USD 100,USD 50,USD,1.2",
            "2026-02-01T09:00:00Z,FAKE,DIVIDEND,,,USD 0.25,USD,1.1",
            "2026-02-02T10:00:00Z,,CASH TOP-UP,,,EUR 20,EUR,1.0",
            "2026-02-03T10:00:00Z,,CASH WITHDRAWAL,,,EUR -5,EUR,1.0",
        )
    )

    assert len(activities) == 4
    assert activities[0] == {
        "import_fingerprint": activities[0]["import_fingerprint"],
        "occurred_at": datetime(2026, 1, 10, 12, 30, tzinfo=UTC),
        "ticker": "FAKE",
        "activity_type": "BUY - MARKET",
        "quantity": Decimal("0.5"),
        "price_per_share": Decimal(100),
        "total_amount": Decimal(50),
        "currency": "USD",
        "fx_rate": Decimal("1.2"),
    }
    assert len(activities[0]["import_fingerprint"]) == 64
    assert activities[1]["activity_type"] == "DIVIDEND"
    assert activities[1]["quantity"] is None
    assert activities[1]["price_per_share"] is None
    assert activities[2]["ticker"] is None
    assert activities[3]["total_amount"] == Decimal(-5)


def test_parse_revolut_investment_csv_rejects_unexpected_headers() -> None:
    source = BytesIO(b"Date,Unexpected\n2026-01-01T00:00:00Z,value\n")

    with pytest.raises(
        ValueError,
        match="Unexpected Revolut investment CSV headers",
    ):
        parse_revolut_investment_csv(source)


@pytest.mark.parametrize(
    "row",
    [
        "2026-01-10T12:30:00Z,,BUY - MARKET,0.5,USD 100,USD 50,USD,1.2",
        "2026-01-10T12:30:00Z,FAKE,UNKNOWN,0.5,USD 100,USD 50,USD,1.2",
        "2026-01-10T12:30:00Z,FAKE,BUY - MARKET,0.5,EUR 100,USD 50,USD,1.2",
        "2026-01-10T12:30:00Z,,CASH WITHDRAWAL,,,EUR 5,EUR,1.0",
    ],
)
def test_parse_revolut_investment_csv_rejects_invalid_rows(row: str) -> None:
    with pytest.raises(ValueError, match="Invalid Revolut investment row 2"):
        parse_revolut_investment_csv(_csv_file(row))
