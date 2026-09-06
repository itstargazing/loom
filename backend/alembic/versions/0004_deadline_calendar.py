"""Add calendar fields to deadlines.

Revision ID: 0004_deadline_calendar
Revises: 0003_skill_stores
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0004_deadline_calendar"
down_revision = "0003_skill_stores"
branch_labels = None
depends_on = None

#  Compared against the model in tests/test_migration_parity.py.
DEADLINE_COLUMNS = {
    "context_snippet",
    "confirmed",
}


def upgrade() -> None:
    op.add_column(
        "deadlines",
        sa.Column(
            "context_snippet",
            sa.Text(),
            nullable=False,
            server_default="",
        ),
    )
    op.add_column(
        "deadlines",
        sa.Column(
            "confirmed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("deadlines", "context_snippet", server_default=None)
    op.alter_column("deadlines", "confirmed", server_default=None)
    op.create_index("ix_deadlines_user_due", "deadlines", ["user_id", "due_date"])


def downgrade() -> None:
    op.drop_index("ix_deadlines_user_due", table_name="deadlines")
    op.drop_column("deadlines", "confirmed")
    op.drop_column("deadlines", "context_snippet")
