from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    name: str
    bank_name: str
    currency: str


class AccountRead(AccountCreate):
    model_config = ConfigDict(from_attributes=True)

    id: int
    current_balance: Decimal | None
    balance_date: date | None


@router.post("", response_model=AccountRead, status_code=status.HTTP_201_CREATED)
def create_account(
    account: AccountCreate,
    session: Annotated[Session, Depends(get_session)],
) -> Account:
    database_account = Account(
        name=account.name,
        bank_name=account.bank_name,
        currency=account.currency,
    )

    session.add(database_account)
    session.commit()
    session.refresh(database_account)

    return database_account


@router.get("", response_model=list[AccountRead])
def list_accounts(
    session: Annotated[Session, Depends(get_session)],
) -> list[Account]:
    accounts = session.scalars(select(Account)).all()
    return list(accounts)
