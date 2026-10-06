from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from investments.calculations import calculate_investment_summary
from models import InvestmentActivity


def _activity(
    *,
    offset: int,
    activity_type: str,
    ticker: str | None = "FAKE",
    quantity: str | None = None,
    total_amount: str,
    currency: str = "USD",
    multiplier: str | None = None,
) -> InvestmentActivity:
    return InvestmentActivity(
        account_id=1,
        import_fingerprint=f"{offset:064x}",
        occurred_at=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(days=offset),
        ticker=ticker,
        activity_type=activity_type,
        quantity=Decimal(quantity) if quantity is not None else None,
        quantity_multiplier=Decimal(multiplier) if multiplier is not None else None,
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


@pytest.mark.parametrize("multiplier", ["1.1", "2", "0.5"])
def test_share_adjustment_changes_quantity_without_changing_cost(
    multiplier: str,
) -> None:
    positions, _ = calculate_investment_summary(
        [
            _activity(
                offset=1, activity_type="BUY - MARKET", quantity="2", total_amount="50"
            ),
            _activity(
                offset=2,
                activity_type="SHARE ADJUSTMENT",
                multiplier=multiplier,
                total_amount="0",
            ),
        ],
        current_prices={"FAKE": Decimal(30)},
    )

    assert positions[0].quantity == Decimal(2) * Decimal(multiplier)
    assert positions[0].remaining_cost == Decimal(50)
    assert positions[0].market_value == positions[0].quantity * Decimal(30)


def test_share_adjustment_preserves_fifo_cost_for_subsequent_sales() -> None:
    positions, _ = calculate_investment_summary(
        [
            _activity(
                offset=1, activity_type="BUY - MARKET", quantity="1", total_amount="100"
            ),
            _activity(
                offset=2, activity_type="BUY - MARKET", quantity="1", total_amount="150"
            ),
            _activity(
                offset=3,
                activity_type="SHARE ADJUSTMENT",
                multiplier="2",
                total_amount="0",
            ),
            _activity(
                offset=4, activity_type="BUY - MARKET", quantity="1", total_amount="80"
            ),
            _activity(
                offset=5,
                activity_type="SELL - MARKET",
                quantity="3",
                total_amount="210",
            ),
        ],
        current_prices={"FAKE": Decimal(70)},
    )

    assert positions[0].quantity == Decimal(2)
    assert positions[0].remaining_cost == Decimal(155)
    assert positions[0].realized_pl == Decimal(35)
    assert positions[0].unrealized_pl == Decimal(-15)


def test_adjustment_is_applied_before_trades_at_the_same_timestamp() -> None:
    positions, _ = calculate_investment_summary(
        [
            _activity(
                offset=1, activity_type="BUY - MARKET", quantity="1", total_amount="50"
            ),
            _activity(
                offset=2, activity_type="BUY - MARKET", quantity="1", total_amount="30"
            ),
            _activity(
                offset=2,
                activity_type="SHARE ADJUSTMENT",
                multiplier="2",
                total_amount="0",
            ),
        ],
        current_prices={},
    )
    assert positions[0].quantity == Decimal(3)
    assert positions[0].remaining_cost == Decimal(80)


@pytest.mark.parametrize("multiplier", [None, "0", "-1", "1", "NaN", "Infinity"])
def test_share_adjustment_rejects_invalid_multiplier(multiplier: str | None) -> None:
    with pytest.raises(ValueError, match="Invalid share adjustment multiplier"):
        calculate_investment_summary(
            [
                _activity(
                    offset=1,
                    activity_type="BUY - MARKET",
                    quantity="1",
                    total_amount="50",
                ),
                _activity(
                    offset=2,
                    activity_type="SHARE ADJUSTMENT",
                    multiplier=multiplier,
                    total_amount="0",
                ),
            ],
            current_prices={},
        )


def test_share_adjustment_rejects_event_before_purchase() -> None:
    with pytest.raises(ValueError, match="Share adjustment requires an open position"):
        calculate_investment_summary(
            [
                _activity(
                    offset=2,
                    activity_type="BUY - MARKET",
                    quantity="1",
                    total_amount="50",
                ),
                _activity(
                    offset=1,
                    activity_type="SHARE ADJUSTMENT",
                    multiplier="2",
                    total_amount="0",
                ),
            ],
            current_prices={},
        )
