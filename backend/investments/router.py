import os
from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from investments.calculations import calculate_investment_summary
from investments.market_prices import (
    MarketPriceError,
    eodhd_symbol_for,
    fetch_eodhd_prices,
)
from investments.revolut_importer import parse_revolut_investment_csv
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
        )
        session.add(investment_price)
    else:
        investment_price.currency = currency
        investment_price.price = price
        investment_price.updated_at = updated_at

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

    return InvestmentSummaryRead(positions=positions, currencies=currencies)


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

    parsed_fingerprints = {
        activity_data["import_fingerprint"] for activity_data in parsed_activities
    }
    existing_fingerprints = set(
        session.scalars(
            select(InvestmentActivity.import_fingerprint).where(
                InvestmentActivity.account_id == account_id,
                InvestmentActivity.import_fingerprint.in_(parsed_fingerprints),
            )
        ).all()
    )

    imported = 0

    for activity_data in parsed_activities:
        fingerprint = activity_data["import_fingerprint"]

        if fingerprint in existing_fingerprints:
            continue

        activity = InvestmentActivity(
            account_id=account_id,
            **activity_data,
        )
        session.add(activity)
        existing_fingerprints.add(fingerprint)
        imported += 1

    session.commit()

    return ImportResult(imported=imported)
