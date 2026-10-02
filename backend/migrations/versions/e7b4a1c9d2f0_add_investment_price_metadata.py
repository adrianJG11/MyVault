"""add investment price source and valuation date

Revision ID: e7b4a1c9d2f0
Revises: 2038594f8fe4
"""

import sqlalchemy as sa
from alembic import op

revision = "e7b4a1c9d2f0"
down_revision = "2038594f8fe4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investment_prices", sa.Column("source", sa.String(20), nullable=True)
    )
    op.add_column(
        "investment_prices", sa.Column("as_of_date", sa.Date(), nullable=True)
    )


def downgrade() -> None:
    op.drop_column("investment_prices", "as_of_date")
    op.drop_column("investment_prices", "source")
