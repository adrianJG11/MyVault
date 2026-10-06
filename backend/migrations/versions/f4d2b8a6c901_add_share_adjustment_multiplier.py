"""add share adjustment multiplier

Revision ID: f4d2b8a6c901
Revises: a4c8e91d6b20
"""

import sqlalchemy as sa
from alembic import op

revision = "f4d2b8a6c901"
down_revision = "a4c8e91d6b20"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "investment_activities",
        sa.Column("quantity_multiplier", sa.Numeric(16, 8), nullable=True),
    )
    op.create_check_constraint(
        "ck_investment_activities_share_adjustment",
        "investment_activities",
        "(activity_type = 'SHARE ADJUSTMENT' AND quantity_multiplier IS NOT NULL "
        "AND quantity_multiplier > 0 AND quantity_multiplier <> 1 "
        "AND quantity_multiplier <> 'NaN'::numeric "
        "AND quantity IS NULL AND price_per_share IS NULL AND total_amount = 0) "
        "OR (activity_type <> 'SHARE ADJUSTMENT' AND quantity_multiplier IS NULL)",
    )


def downgrade() -> None:
    if op.get_bind().scalar(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM investment_activities "
            "WHERE activity_type = 'SHARE ADJUSTMENT')"
        )
    ):
        raise RuntimeError("Cannot downgrade while share adjustments are recorded")
    op.drop_constraint(
        "ck_investment_activities_share_adjustment",
        "investment_activities",
        type_="check",
    )
    op.drop_column("investment_activities", "quantity_multiplier")
