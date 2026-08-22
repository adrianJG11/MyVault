from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from investment_calculations import calculate_investment_summary
from models import InvestmentActivity


def _activity(
    *,
    offset: int,
    activity_type: str,
    ticker: str | None = "FAKE",
    quantity: str | None = None,
    total_amount: str,
    currency: str = "USD",
) -> InvestmentActivity:
    return InvestmentActivity(
        account_id=1,
        import_fingerprint=f"{offset:064x}",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=offset),
        ticker=ticker,
        activity_type=activity_type,
        quantity=Decimal(quantity) if quantity is not None else None,
        price_per_share=None,
        total_amount=Decimal(total_amount),
        currency=currency,
        fx_rate=Decimal(1),
    )


def test_calculate_investment_summary_uses_fifo_and_current_price() -> None:
    positions, summaries = calculate_investment_summary(
        [
            _activity(
                offset=1, activity_type="BUY - MARKET", quantity="1", total_amount="100"
            ),
            _activity(
                offset=2, activity_type="BUY - MARKET", quantity="1", total_amount="150"
            ),
            _activity(
                offset=3,
                activity_type="SELL - MARKET",
                quantity="1.5",
                total_amount="210",
            ),
            _activity(offset=4, activity_type="DIVIDEND", total_amount="2"),
        ],
        current_prices={"FAKE": Decimal(160)},
    )

    assert len(positions) == 1
    position = positions[0]
    assert position.quantity == Decimal("0.5")
    assert position.remaining_cost == Decimal(75)
    assert position.market_value == Decimal(80)
    assert position.unrealized_pl == Decimal(5)
    assert position.unrealized_return_percent == Decimal(
        "6.666666666666666666666666667"
    )
    assert position.realized_pl == Decimal(35)
    assert position.dividends == Decimal(2)
    assert position.total_result == Decimal(42)

    assert len(summaries) == 1
    summary = summaries[0]
    assert summary.currency == "USD"
    assert summary.total_result == Decimal(42)
    assert summary.priced_positions == 1
    assert summary.total_open_positions == 1


def test_calculate_investment_summary_keeps_unpriced_totals_unknown() -> None:
    positions, summaries = calculate_investment_summary(
        [
            _activity(
                offset=1, activity_type="BUY - MARKET", quantity="2", total_amount="50"
            ),
            _activity(
                offset=2,
                activity_type="CASH TOP-UP",
                ticker=None,
                total_amount="50",
            ),
        ],
        current_prices={},
    )

    assert positions[0].market_value is None
    assert positions[0].unrealized_pl is None
    assert positions[0].total_result is None
    assert summaries[0].market_value is None
    assert summaries[0].total_result is None
    assert summaries[0].priced_positions == 0


def test_calculate_investment_summary_rejects_sell_without_enough_shares() -> None:
    activities = [
        _activity(
            offset=1, activity_type="BUY - MARKET", quantity="1", total_amount="100"
        ),
        _activity(
            offset=2, activity_type="SELL - MARKET", quantity="2", total_amount="200"
        ),
    ]

    with pytest.raises(ValueError, match="Sell quantity exceeds available position"):
        calculate_investment_summary(activities, current_prices={})
