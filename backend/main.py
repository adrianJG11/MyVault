import os
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from ibercaja_importer import parse_ibercaja_xlsx
from investment_calculations import calculate_investment_summary
from market_prices import MarketPriceError, fetch_twelve_data_prices
from models import Account, InvestmentActivity, InvestmentPrice, Transaction
from revolut_investment_importer import parse_revolut_investment_csv


class AccountCreate(BaseModel):
    name: str
    bank_name: str
    currency: str


class AccountRead(AccountCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int


class TransactionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    account_id: int
    operation_date: date
    value_date: date
    amount: Decimal
    balance_after: Decimal
    bank_concept: str
    description: str


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


class ImportResult(BaseModel):
    imported: int


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


app = FastAPI()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/accounts", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    account: AccountCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Account:
    database_account = Account(
        name=account.name, bank_name=account.bank_name, currency=account.currency
    )

    session.add(database_account)
    session.commit()
    session.refresh(database_account)

    return database_account


@app.get("/accounts", response_model=list[AccountRead])
def list_accounts(
    session: Annotated[Session, Depends(get_session)],
) -> list[Account]:
    statement = select(Account)
    accounts = session.scalars(statement).all()
    return list(accounts)


@app.get("/transactions", response_model=list[TransactionRead])
def list_transactions(
    session: Annotated[Session, Depends(get_session)],
    account_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    description: str | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
) -> list[Transaction]:
    if date_from is not None and date_to is not None and date_from > date_to:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="date_from must be before or equal to date_to",
        )

    if amount_min is not None and amount_max is not None and amount_min > amount_max:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="amount_min must be less than or equal to amount_max",
        )

    statement = select(Transaction)

    if description is not None:
        statement = statement.where(Transaction.description.ilike(f"%{description}%"))

    if account_id is not None:
        statement = statement.where(Transaction.account_id == account_id)

    if date_from is not None:
        statement = statement.where(Transaction.operation_date >= date_from)

    if date_to is not None:
        statement = statement.where(Transaction.operation_date <= date_to)

    if amount_min is not None:
        statement = statement.where(Transaction.amount >= amount_min)

    if amount_max is not None:
        statement = statement.where(Transaction.amount <= amount_max)

    statement = statement.order_by(
        Transaction.operation_date.desc(),
        Transaction.id.desc(),
    )

    transactions = session.scalars(statement).all()
    return list(transactions)


@app.get("/investment-activities", response_model=list[InvestmentActivityRead])
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


@app.get("/investment-summary", response_model=InvestmentSummaryRead)
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


@app.put(
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


@app.post(
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
    automatic_positions = [
        position for position in open_positions if position.currency == "USD"
    ]
    manual_only = sorted(
        position.ticker for position in open_positions if position.currency != "USD"
    )

    if not automatic_positions:
        return InvestmentPriceRefreshResult(
            updated=[],
            unavailable=[],
            manual_only=manual_only,
        )

    api_key = os.getenv("TWELVE_DATA_API_KEY", "").strip()

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Market price API is not configured",
        )

    try:
        result = fetch_twelve_data_prices(
            [position.ticker for position in automatic_positions],
            api_key,
        )
    except MarketPriceError as error:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Market price provider unavailable",
        ) from error

    currencies = {
        position.ticker: position.currency for position in automatic_positions
    }
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


@app.post(
    "/accounts/{account_id}/imports/ibercaja",
    response_model=ImportResult,
    status_code=status.HTTP_201_CREATED,
)
def import_ibercaja_transactions(
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
        parsed_transactions = parse_ibercaja_xlsx(file.file)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Invalid Ibercaja workbook",
        ) from error

    parsed_fingerprints = {
        transaction_data["import_fingerprint"]
        for transaction_data in parsed_transactions
    }
    existing_fingerprints = set(
        session.scalars(
            select(Transaction.import_fingerprint).where(
                Transaction.account_id == account_id,
                Transaction.import_fingerprint.in_(parsed_fingerprints),
            )
        ).all()
    )

    imported = 0

    for transaction_data in parsed_transactions:
        fingerprint = transaction_data["import_fingerprint"]

        if fingerprint in existing_fingerprints:
            continue

        transaction = Transaction(
            account_id=account_id,
            **transaction_data,
        )
        session.add(transaction)

        existing_fingerprints.add(fingerprint)
        imported += 1

    session.commit()

    return ImportResult(imported=imported)


@app.post(
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
