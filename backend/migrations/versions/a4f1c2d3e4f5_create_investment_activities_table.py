"""create investment activities table

Revision ID: a4f1c2d3e4f5
Revises: d10ed3e166ab
Create Date: 2026-08-21 20:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a4f1c2d3e4f5"
down_revision: str | Sequence[str] | None = "d10ed3e166ab"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Create the table for imported investment activity."""
    op.create_table(
        "investment_activities",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("account_id", sa.Integer(), nullable=False),
        sa.Column("import_fingerprint", sa.String(length=64), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ticker", sa.String(length=20), nullable=True),
        sa.Column("activity_type", sa.String(length=30), nullable=False),
        sa.Column("quantity", sa.Numeric(precision=24, scale=12), nullable=True),
        sa.Column(
            "price_per_share",
            sa.Numeric(precision=24, scale=8),
            nullable=True,
        ),
        sa.Column("total_amount", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column("currency", sa.String(length=3), nullable=False),
        sa.Column("fx_rate", sa.Numeric(precision=24, scale=8), nullable=False),
        sa.ForeignKeyConstraint(["account_id"], ["accounts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "account_id",
            "import_fingerprint",
            name="uq_investment_activities_account_import_fingerprint",
        ),
    )


def downgrade() -> None:
    """Remove the investment activity table."""
    op.drop_table("investment_activities")
