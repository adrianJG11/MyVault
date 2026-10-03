from datetime import date
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from database import get_session
from models import Account

router = APIRouter(prefix="/accounts", tags=["accounts"])


class AccountCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=100)
    bank_name: str = Field(min_length=1, max_length=100)
    currency: str = Field(pattern=r"^[A-Z]{3}$")

    @field_validator("currency", mode="before")
    @classmethod
    def normalize_currency(cls, value: object) -> object:
        if isinstance(value, str):
            return value.strip().upper()
        return value


class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    bank_name: str
    currency: str
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
