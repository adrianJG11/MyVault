import os
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DataError
from sqlalchemy.orm import Session

from database import get_session
from investments.calculations import calculate_investment_summary
from investments.ibkr_parser import ParsedIBKRPrice, parse_ibkr_report
from investments.market_prices import (
    MarketPriceError,
    eodhd_symbol_for,
    fetch_eodhd_prices,
)
from investments.revolut_importer import (
    ParsedInvestmentActivity,
    parse_revolut_investment_csv,
)
from models import Account, InvestmentActivity, InvestmentPrice
from schemas import ImportResult

router = APIRouter(tags=["investments"])


class InvestmentActivityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    occurred_at: datetime
    ticker: str | None
    activity_type: str
    quantity: Decimal | None
    price_per_share: Decimal | None
    total_amount: Decimal
    currency: str
    fx_rate: Decimal


class InvestmentPriceUpdate(BaseModel):
    price: Decimal = Field(gt=0)


class InvestmentPriceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    currency: str
    price: Decimal
    updated_at: datetime
    source: str | None
    as_of_date: date | None


class IBKRImportResult(ImportResult):
    prices_updated: int


class InvestmentPriceRefreshResult(BaseModel):
    updated: list[str]
    unavailable: list[str]
    manual_only: list[str]


class InvestmentPositionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    ticker: str
    currency: str
    quantity: Decimal
    remaining_cost: Decimal
    current_price: Decimal | None
    price_source: str | None = None
    price_as_of: date | None = None
    price_updated_at: datetime | None = None
    market_value: Decimal | None
    unrealized_pl: Decimal | None
    unrealized_return_percent: Decimal | None
    realized_pl: Decimal
    dividends: Decimal
    total_result: Decimal | None


class InvestmentCurrencySummaryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str
    remaining_cost: Decimal
    market_value: Decimal | None
    unrealized_pl: Decimal | None
    realized_pl: Decimal
    dividends: Decimal
    total_result: Decimal | None
    priced_positions: int
    total_open_positions: int


class InvestmentSummaryRead(BaseModel):
    positions: list[InvestmentPositionRead]
    currencies: list[InvestmentCurrencySummaryRead]


def _set_investment_price(
    session: Session,
    account_id: int,
    ticker: str,
    currency: str,
    price: Decimal,
    updated_at: datetime,
    source: str = "manual",
    as_of_date: date | None = None,
) -> InvestmentPrice:
    investment_price = session.scalar(
        select(InvestmentPrice).where(
            InvestmentPrice.account_id == account_id,
            InvestmentPrice.ticker == ticker,
        )
    )

    if investment_price is None:
        investment_price = InvestmentPrice(
            account_id=account_id,
            ticker=ticker,
            currency=currency,
            price=price,
            updated_at=updated_at,
            source=source,
            as_of_date=as_of_date,
        )
        session.add(investment_price)
    else:
        investment_price.currency = currency
        investment_price.price = price
        investment_price.updated_at = updated_at
        investment_price.source = source
        investment_price.as_of_date = as_of_date

    return investment_price


@router.get("/investment-activities", response_model=list[InvestmentActivityRead])
def list_investment_activities(
    session: Annotated[Session, Depends(get_session)],
    account_id: int | None = None,
) -> list[InvestmentActivity]:
    statement = select(InvestmentActivity)

    if account_id is not None:
        statement = statement.where(InvestmentActivity.account_id == account_id)

    statement = statement.order_by(
        InvestmentActivity.occurred_at.desc(),
        InvestmentActivity.id.desc(),
    )

    activities = session.scalars(statement).all()
    return list(activities)


@router.get("/investment-summary", response_model=InvestmentSummaryRead)
def get_investment_summary(
    account_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> InvestmentSummaryRead:
    account = session.get(Account, account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    activities = session.scalars(
        select(InvestmentActivity).where(InvestmentActivity.account_id == account_id)
    ).all()
    prices = session.scalars(
        select(InvestmentPrice).where(InvestmentPrice.account_id == account_id)
    ).all()

    try:
        positions, currencies = calculate_investment_summary(
            activities,
            current_prices={price.ticker: price.price for price in prices},
        )
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Investment history cannot be calculated",
        ) from error

    prices_by_ticker = {price.ticker: price for price in prices}
    position_reads = []
    for position in positions:
        position_read = InvestmentPositionRead.model_validate(position)
        price = prices_by_ticker.get(position.ticker)
        if price is not None:
            position_read.price_source = price.source
            position_read.price_as_of = price.as_of_date
            position_read.price_updated_at = price.updated_at
        position_reads.append(position_read)
    return InvestmentSummaryRead(positions=position_reads, currencies=currencies)


@router.put(
    "/accounts/{account_id}/investment-prices/{ticker}",
    response_model=InvestmentPriceRead,
)
def update_investment_price(
    account_id: int,
    ticker: str,
    price_update: InvestmentPriceUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> InvestmentPrice:
    account = session.get(Account, account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    normalized_ticker = ticker.strip().upper()

    if not normalized_ticker or len(normalized_ticker) > 20:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid ticker",
        )

    currencies = set(
        session.scalars(
            select(InvestmentActivity.currency)
            .where(
                InvestmentActivity.account_id == account_id,
                InvestmentActivity.ticker == normalized_ticker,
            )
            .distinct()
        ).all()
    )

    if not currencies:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ticker not found",
        )

    if len(currencies) != 1:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ticker uses multiple currencies",
        )

    investment_price = _set_investment_price(
        session=session,
        account_id=account_id,
        ticker=normalized_ticker,
        currency=currencies.pop(),
        price=price_update.price,
        updated_at=datetime.now(UTC),
    )

    session.commit()
    session.refresh(investment_price)
    return investment_price


@router.post(
    "/accounts/{account_id}/investment-prices/refresh",
    response_model=InvestmentPriceRefreshResult,
)
def refresh_investment_prices(
    account_id: int,
    session: Annotated[Session, Depends(get_session)],
) -> InvestmentPriceRefreshResult:
    account = session.get(Account, account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    activities = session.scalars(
        select(InvestmentActivity).where(InvestmentActivity.account_id == account_id)
    ).all()

    try:
        positions, _ = calculate_investment_summary(activities, current_prices={})
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Investment history cannot be calculated",
        ) from error

    open_positions = [position for position in positions if position.quantity > 0]
    provider_symbols = {
        position.ticker: provider_symbol
        for position in open_positions
        if (provider_symbol := eodhd_symbol_for(position.ticker, position.currency))
        is not None
    }
    manual_only = sorted(
        position.ticker
        for position in open_positions
        if position.ticker not in provider_symbols
    )

    if not provider_symbols:
        return InvestmentPriceRefreshResult(
            updated=[],
            unavailable=[],
            manual_only=manual_only,
        )

    api_key = os.getenv("EODHD_API_KEY", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market price API is not configured",
        )

    try:
        result = fetch_eodhd_prices(provider_symbols, api_key)
    except MarketPriceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Market price provider unavailable",
        ) from error

    currencies = {position.ticker: position.currency for position in open_positions}
    updated_at = datetime.now(UTC)

    for ticker, price in result.prices.items():
        _set_investment_price(
            session=session,
            account_id=account_id,
            ticker=ticker,
            currency=currencies[ticker],
            price=price,
            updated_at=updated_at,
            source="eodhd",
        )

    session.commit()

    return InvestmentPriceRefreshResult(
        updated=sorted(result.prices),
        unavailable=result.unavailable,
        manual_only=manual_only,
    )


@router.post(
    "/accounts/{account_id}/imports/revolut-investments",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
)
def import_revolut_investment_activities(
    account_id: int,
    file: UploadFile,
    session: Annotated[Session, Depends(get_session)],
) -> ImportResult:
    account = session.get(Account, account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )

    try:
        parsed_activities = parse_revolut_investment_csv(file.file)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid Revolut investment CSV",
        ) from error

    imported, _ = _store_investment_activities(session, account_id, parsed_activities)
    return ImportResult(imported=imported)


@router.post(
    "/accounts/{account_id}/imports/ibkr-investments",
    response_model=IBKRImportResult,
    status_code=status.HTTP_201_CREATED,
)
def import_ibkr_investment_activities(
    account_id: int,
    file: UploadFile,
    session: Annotated[Session, Depends(get_session)],
) -> IBKRImportResult:
    account = session.get(Account, account_id)

    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found",
        )
    try:
        parsed_ibkr, prices = parse_ibkr_report(file.file)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid IBKR report",
        ) from error

    imported, prices_updated = _store_investment_activities(
        session, account_id, parsed_ibkr, prices
    )
    return IBKRImportResult(imported=imported, prices_updated=prices_updated)


def _store_investment_activities(
    session: Session,
    account_id: int,
    parsed_activities: list[ParsedInvestmentActivity],
    prices: list[ParsedIBKRPrice] | None = None,
) -> tuple[int, int]:
    imported = 0
    prices_updated = 0
    try:
        for start in range(0, len(parsed_activities), 500):
            statement = (
                insert(InvestmentActivity)
                .values(
                    [
                        {"account_id": account_id, **activity}
                        for activity in parsed_activities[start : start + 500]
                    ]
                )
                .on_conflict_do_nothing(
                    index_elements=["account_id", "import_fingerprint"]
                )
                .returning(InvestmentActivity.id)
            )
            imported += len(session.scalars(statement).all())
        for price in prices or []:
            currencies = set(
                session.scalars(
                    select(InvestmentActivity.currency).where(
                        InvestmentActivity.account_id == account_id,
                        InvestmentActivity.ticker == price.ticker,
                    )
                ).all()
            )
            if currencies != {price.currency}:
                raise ValueError(
                    "IBKR prices require matching trade history and currency"
                )
            values = {
                "account_id": account_id,
                "ticker": price.ticker,
                "currency": price.currency,
                "price": price.price,
                "as_of_date": price.as_of_date,
                "source": "ibkr",
                "updated_at": datetime.now(UTC),
            }
            statement = (
                insert(InvestmentPrice)
                .values(values)
                .on_conflict_do_update(
                    index_elements=["account_id", "ticker"],
                    set_={
                        key: value
                        for key, value in values.items()
                        if key not in {"account_id", "ticker"}
                    },
                    where=price.as_of_date
                    > func.coalesce(
                        InvestmentPrice.as_of_date,
                        func.date(InvestmentPrice.updated_at),
                    ),
                )
                .returning(InvestmentPrice.id)
            )
            prices_updated += session.scalar(statement) is not None
        session.commit()
    except DataError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Investment values cannot be stored",
        ) from error
    except ValueError as error:
        session.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    return imported, prices_updated
