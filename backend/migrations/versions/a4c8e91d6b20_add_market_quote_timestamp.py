"""add market quote timestamp

Revision ID: a4c8e91d6b20
Revises: e7b4a1c9d2f0
"""

import sqlalchemy as sa
from alembic import op

revision = "a4c8e91d6b20"
down_revision = "e7b4a1c9d2f0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investment_prices",
        sa.Column("quoted_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("investment_prices", "quoted_at")
