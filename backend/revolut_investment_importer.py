import csv
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from hashlib import sha256
from io import TextIOWrapper
from typing import BinaryIO, TypedDict

EXPECTED_HEADERS = (
    "Date",
    "Ticker",
    "Type",
    "Quantity",
    "Price per share",
    "Total Amount",
    "Currency",
    "FX Rate",
)

MARKET_ACTIVITY_TYPES = {"BUY - MARKET", "SELL - MARKET"}
CASH_ACTIVITY_TYPES = {"CASH TOP-UP", "CASH WITHDRAWAL"}
SUPPORTED_ACTIVITY_TYPES = MARKET_ACTIVITY_TYPES | CASH_ACTIVITY_TYPES | {"DIVIDEND"}


class ParsedInvestmentActivity(TypedDict):
    import_fingerprint: str
    occurred_at: datetime
    ticker: str | None
    activity_type: str
    quantity: Decimal | None
    price_per_share: Decimal | None
    total_amount: Decimal
    currency: str
    fx_rate: Decimal


def _invalid_row(row_number: int) -> ValueError:
    return ValueError(f"Invalid Revolut investment row {row_number}")


def _required_value(
    row: dict[str | None, str | list[str] | None],
    field: str,
    row_number: int,
) -> str:
    value = row.get(field)

    if not isinstance(value, str) or not value.strip():
        raise _invalid_row(row_number)

    return value.strip()


def _optional_value(
    row: dict[str | None, str | list[str] | None],
    field: str,
) -> str | None:
    value = row.get(field)

    if not isinstance(value, str) or not value.strip():
        return None

    return value.strip()


def _parse_decimal(value: str, row_number: int) -> Decimal:
    try:
        return Decimal(value)
    except InvalidOperation as error:
        raise _invalid_row(row_number) from error


def _parse_money(
    value: str,
    expected_currency: str,
    row_number: int,
) -> Decimal:
    parts = value.split(maxsplit=1)

    if len(parts) != 2 or parts[0] != expected_currency:
        raise _invalid_row(row_number)

    return _parse_decimal(parts[1], row_number)


def _decimal_text(value: Decimal | None) -> str | None:
    if value is None:
        return None

    return format(value.normalize(), "f")


def _create_import_fingerprint(
    *,
    occurred_at: datetime,
    ticker: str | None,
    activity_type: str,
    quantity: Decimal | None,
    price_per_share: Decimal | None,
    total_amount: Decimal,
    currency: str,
    fx_rate: Decimal,
) -> str:
    canonical_values = json.dumps(
        [
            occurred_at.isoformat(),
            ticker,
            activity_type,
            _decimal_text(quantity),
            _decimal_text(price_per_share),
            _decimal_text(total_amount),
            currency,
            _decimal_text(fx_rate),
        ],
        separators=(",", ":"),
    )
    return sha256(
        canonical_values.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()


def parse_revolut_investment_csv(
    source: BinaryIO,
) -> list[ParsedInvestmentActivity]:
    text_source = TextIOWrapper(source, encoding="utf-8-sig", newline="")

    try:
        reader = csv.DictReader(text_source)

        if tuple(reader.fieldnames or ()) != EXPECTED_HEADERS:
            raise ValueError("Unexpected Revolut investment CSV headers")

        activities: list[ParsedInvestmentActivity] = []

        for row_number, row in enumerate(reader, start=2):
            if None in row:
                raise _invalid_row(row_number)

            occurred_at_text = _required_value(row, "Date", row_number)
            activity_type = _required_value(row, "Type", row_number)
            currency = _required_value(row, "Currency", row_number)
            total_amount_text = _required_value(row, "Total Amount", row_number)
            fx_rate_text = _required_value(row, "FX Rate", row_number)

            if activity_type not in SUPPORTED_ACTIVITY_TYPES:
                raise _invalid_row(row_number)

            if len(currency) != 3 or not currency.isalpha() or not currency.isupper():
                raise _invalid_row(row_number)

            try:
                occurred_at = datetime.fromisoformat(occurred_at_text)
            except ValueError as error:
                raise _invalid_row(row_number) from error

            if occurred_at.utcoffset() is None:
                raise _invalid_row(row_number)

            occurred_at = occurred_at.astimezone(UTC)
            ticker = _optional_value(row, "Ticker")
            quantity_text = _optional_value(row, "Quantity")
            price_text = _optional_value(row, "Price per share")
            total_amount = _parse_money(
                total_amount_text,
                currency,
                row_number,
            )
            fx_rate = _parse_decimal(fx_rate_text, row_number)

            if fx_rate <= 0:
                raise _invalid_row(row_number)

            quantity: Decimal | None = None
            price_per_share: Decimal | None = None

            if activity_type in MARKET_ACTIVITY_TYPES:
                if ticker is None or quantity_text is None or price_text is None:
                    raise _invalid_row(row_number)

                quantity = _parse_decimal(quantity_text, row_number)
                price_per_share = _parse_money(price_text, currency, row_number)

                if quantity <= 0 or price_per_share <= 0 or total_amount <= 0:
                    raise _invalid_row(row_number)
            elif activity_type == "DIVIDEND":
                if (
                    ticker is None
                    or quantity_text is not None
                    or price_text is not None
                    or total_amount <= 0
                ):
                    raise _invalid_row(row_number)
            else:
                if (
                    ticker is not None
                    or quantity_text is not None
                    or price_text is not None
                ):
                    raise _invalid_row(row_number)

                if activity_type == "CASH TOP-UP" and total_amount <= 0:
                    raise _invalid_row(row_number)

                if activity_type == "CASH WITHDRAWAL" and total_amount >= 0:
                    raise _invalid_row(row_number)

            if ticker is not None and len(ticker) > 20:
                raise _invalid_row(row_number)

            fingerprint = _create_import_fingerprint(
                occurred_at=occurred_at,
                ticker=ticker,
                activity_type=activity_type,
                quantity=quantity,
                price_per_share=price_per_share,
                total_amount=total_amount,
                currency=currency,
                fx_rate=fx_rate,
            )
            activities.append(
                {
                    "import_fingerprint": fingerprint,
                    "occurred_at": occurred_at,
                    "ticker": ticker,
                    "activity_type": activity_type,
                    "quantity": quantity,
                    "price_per_share": price_per_share,
                    "total_amount": total_amount,
                    "currency": currency,
                    "fx_rate": fx_rate,
                }
            )

        return activities
    except (csv.Error, UnicodeDecodeError) as error:
        raise ValueError("Invalid Revolut investment CSV") from error
    finally:
        text_source.detach()
