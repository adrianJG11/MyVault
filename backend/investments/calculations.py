from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from models import InvestmentActivity

ZERO = Decimal(0)
HUNDRED = Decimal(100)


@dataclass(frozen=True)
class InvestmentPosition:
    ticker: str
    currency: str
    quantity: Decimal
    remaining_cost: Decimal
    current_price: Decimal | None
    market_value: Decimal | None
    unrealized_pl: Decimal | None
    unrealized_return_percent: Decimal | None
    realized_pl: Decimal
    dividends: Decimal
    total_result: Decimal | None


@dataclass(frozen=True)
class InvestmentCurrencySummary:
    currency: str
    remaining_cost: Decimal
    market_value: Decimal | None
    unrealized_pl: Decimal | None
    realized_pl: Decimal
    dividends: Decimal
    total_result: Decimal | None
    priced_positions: int
    total_open_positions: int


@dataclass
class _Lot:
    quantity: Decimal
    unit_cost: Decimal


@dataclass
class _PositionState:
    currency: str
    lots: list[_Lot] = field(default_factory=list)
    realized_pl: Decimal = ZERO
    dividends: Decimal = ZERO


def _position_state(
    states: dict[str, _PositionState],
    activity: InvestmentActivity,
) -> _PositionState:
    if activity.ticker is None:
        raise ValueError("Ticker is required for investment calculations")

    state = states.get(activity.ticker)

    if state is None:
        state = _PositionState(currency=activity.currency)
        states[activity.ticker] = state
    elif state.currency != activity.currency:
        raise ValueError("A ticker cannot use multiple currencies")

    return state


def calculate_investment_summary(
    activities: Iterable[InvestmentActivity],
    current_prices: Mapping[str, Decimal],
) -> tuple[list[InvestmentPosition], list[InvestmentCurrencySummary]]:
    states: dict[str, _PositionState] = {}
    ordered_activities = sorted(
        activities,
        key=lambda activity: (activity.occurred_at, activity.id or 0),
    )

    for activity in ordered_activities:
        if activity.activity_type in {"CASH TOP-UP", "CASH WITHDRAWAL"}:
            continue

        state = _position_state(states, activity)

        if activity.activity_type == "BUY - MARKET":
            if activity.quantity is None or activity.quantity <= 0:
                raise ValueError("Buy quantity must be positive")

            state.lots.append(
                _Lot(
                    quantity=activity.quantity,
                    unit_cost=activity.total_amount / activity.quantity,
                )
            )
        elif activity.activity_type == "SELL - MARKET":
            if activity.quantity is None or activity.quantity <= 0:
                raise ValueError("Sell quantity must be positive")

            quantity_to_sell = activity.quantity
            sold_cost = ZERO

            while quantity_to_sell > 0 and state.lots:
                lot = state.lots[0]
                consumed_quantity = min(quantity_to_sell, lot.quantity)
                sold_cost += consumed_quantity * lot.unit_cost
                lot.quantity -= consumed_quantity
                quantity_to_sell -= consumed_quantity

                if lot.quantity == 0:
                    state.lots.pop(0)

            if quantity_to_sell > 0:
                raise ValueError("Sell quantity exceeds available position")

            state.realized_pl += activity.total_amount - sold_cost
        elif activity.activity_type == "DIVIDEND":
            state.dividends += activity.total_amount
        else:
            raise ValueError("Unsupported investment activity type")

    positions: list[InvestmentPosition] = []

    for ticker, state in sorted(states.items()):
        quantity = sum((lot.quantity for lot in state.lots), start=ZERO)
        remaining_cost = sum(
            (lot.quantity * lot.unit_cost for lot in state.lots),
            start=ZERO,
        )
        current_price = current_prices.get(ticker)

        if quantity == 0:
            market_value: Decimal | None = ZERO
            unrealized_pl: Decimal | None = ZERO
            unrealized_return_percent: Decimal | None = None
        elif current_price is None:
            market_value = None
            unrealized_pl = None
            unrealized_return_percent = None
        else:
            market_value = quantity * current_price
            unrealized_pl = market_value - remaining_cost
            unrealized_return_percent = (
                unrealized_pl / remaining_cost * HUNDRED
                if remaining_cost != 0
                else None
            )

        total_result = (
            state.realized_pl + state.dividends + unrealized_pl
            if unrealized_pl is not None
            else None
        )
        positions.append(
            InvestmentPosition(
                ticker=ticker,
                currency=state.currency,
                quantity=quantity,
                remaining_cost=remaining_cost,
                current_price=current_price,
                market_value=market_value,
                unrealized_pl=unrealized_pl,
                unrealized_return_percent=unrealized_return_percent,
                realized_pl=state.realized_pl,
                dividends=state.dividends,
                total_result=total_result,
            )
        )

    summaries: list[InvestmentCurrencySummary] = []

    for currency in sorted({position.currency for position in positions}):
        currency_positions = [
            position for position in positions if position.currency == currency
        ]
        open_positions = [
            position for position in currency_positions if position.quantity > 0
        ]
        all_open_positions_priced = all(
            position.current_price is not None for position in open_positions
        )
        remaining_cost = sum(
            (position.remaining_cost for position in currency_positions),
            start=ZERO,
        )
        realized_pl = sum(
            (position.realized_pl for position in currency_positions),
            start=ZERO,
        )
        dividends = sum(
            (position.dividends for position in currency_positions),
            start=ZERO,
        )

        if all_open_positions_priced:
            market_value = sum(
                (
                    position.market_value
                    for position in currency_positions
                    if position.market_value is not None
                ),
                start=ZERO,
            )
            unrealized_pl = market_value - remaining_cost
            total_result = realized_pl + dividends + unrealized_pl
        else:
            market_value = None
            unrealized_pl = None
            total_result = None

        summaries.append(
            InvestmentCurrencySummary(
                currency=currency,
                remaining_cost=remaining_cost,
                market_value=market_value,
                unrealized_pl=unrealized_pl,
                realized_pl=realized_pl,
                dividends=dividends,
                total_result=total_result,
                priced_positions=sum(
                    position.current_price is not None for position in open_positions
                ),
                total_open_positions=len(open_positions),
            )
        )

    return positions, summaries
