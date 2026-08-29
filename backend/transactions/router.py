from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import Account, Transaction
from schemas import ImportResult
from transactions.categorization import suggest_transaction_category
from transactions.ibercaja_importer import parse_ibercaja_xlsx

router = APIRouter(tags=["transactions"])


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
    category: str | None


class TransactionCategoryUpdate(BaseModel):
    category: str = Field(min_length=1, max_length=125)


@router.get("/transactions", response_model=list[TransactionRead])
def list_transactions(
    session: Annotated[Session, Depends(get_session)],
    account_id: int | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    description: str | None = None,
    amount_min: Decimal | None = None,
    amount_max: Decimal | None = None,
    category: str | None = None,
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

    if category == "uncategorized":
        statement = statement.where(Transaction.category.is_(None))
    elif category is not None:
        statement = statement.where(Transaction.category == category)

    statement = statement.order_by(
        Transaction.operation_date.desc(),
        Transaction.id.desc(),
    )

    transactions = session.scalars(statement).all()
    return list(transactions)


@router.patch(
    "/transactions/{transaction_id}/category",
    response_model=TransactionRead,
)
def update_transaction_category(
    transaction_id: int,
    category_update: TransactionCategoryUpdate,
    session: Annotated[Session, Depends(get_session)],
) -> Transaction:
    transaction = session.get(Transaction, transaction_id)

    if transaction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Transaction not found",
        )

    transaction.category = category_update.category
    session.commit()
    session.refresh(transaction)

    return transaction


@router.post(
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

    if parsed_transactions:
        latest_transaction = parsed_transactions[0]
        latest_date = latest_transaction["operation_date"]

        if account.balance_date is None or latest_date >= account.balance_date:
            account.current_balance = latest_transaction["balance_after"]
            account.balance_date = latest_date

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
            category=suggest_transaction_category(
                transaction_data["description"],
            ),
            **transaction_data,
        )
        session.add(transaction)
        existing_fingerprints.add(fingerprint)
        imported += 1

    session.commit()

    return ImportResult(imported=imported)
