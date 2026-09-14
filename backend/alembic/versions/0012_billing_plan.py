"""Billing plan fields + retention is config-only (no schema).

Revision ID: 0012_billing_plan
Revises: 0011_breakthrough
Create Date: 2026-09-14
"""

import sqlalchemy as sa
from alembic import op

revision = "0012_billing_plan"
down_revision = "0011_breakthrough"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_accounts",
        sa.Column("plan", sa.String(length=32), nullable=False, server_default="free"),
    )
    op.add_column(
        "user_accounts",
        sa.Column("stripe_customer_id", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "user_accounts",
        sa.Column("stripe_subscription_id", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("user_accounts", "stripe_subscription_id")
    op.drop_column("user_accounts", "stripe_customer_id")
    op.drop_column("user_accounts", "plan")
