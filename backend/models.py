from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    bank_name: Mapped[str] = mapped_column(String(100))
    currency: Mapped[str] = mapped_column(String(3))


class Transaction(Base):
    __tablename__ = "transactions"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "import_fingerprint",
            name="uq_transactions_account_import_fingerprint",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    import_fingerprint: Mapped[str] = mapped_column(String(64))
    operation_date: Mapped[date] = mapped_column()
    value_date: Mapped[date] = mapped_column()
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    balance_after: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    bank_concept: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(255))


class InvestmentActivity(Base):
    __tablename__ = "investment_activities"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "import_fingerprint",
            name="uq_investment_activities_account_import_fingerprint",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    import_fingerprint: Mapped[str] = mapped_column(String(64))
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    ticker: Mapped[str | None] = mapped_column(String(20))
    activity_type: Mapped[str] = mapped_column(String(30))
    quantity: Mapped[Decimal | None] = mapped_column(Numeric(24, 12))
    price_per_share: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    total_amount: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    currency: Mapped[str] = mapped_column(String(3))
    fx_rate: Mapped[Decimal] = mapped_column(Numeric(24, 8))


class InvestmentPrice(Base):
    __tablename__ = "investment_prices"
    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "ticker",
            name="uq_investment_prices_account_ticker",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"))
    ticker: Mapped[str] = mapped_column(String(20))
    currency: Mapped[str] = mapped_column(String(3))
    price: Mapped[Decimal] = mapped_column(Numeric(24, 8))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
