"""create investment prices table

Revision ID: b5e2d3c4f5a6
Revises: a4f1c2d3e4f5
Create Date: 2026-08-21 21:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b5e2d3c4f5a6"
down_revision: str | Sequence[str] | None = "a4f1c2d3e4f5"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table for manually entered current prices."""
    op.create_table(
        "investment_prices",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("price", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "ticker",
            name="uq_investment_prices_account_ticker",
        ),
    )


def downgrade() -> None:
    """Remove manually entered current prices."""
    op.drop_table("investment_prices")
