"""Track dismissed contradiction pairs so the watcher does not re-flag them.

Revision ID: 0005_contradiction_dismiss
Revises: 0004_deadline_calendar
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0005_contradiction_dismiss"
down_revision = "0004_deadline_calendar"
branch_labels = None
depends_on = None

#  Compared against the model in tests/test_migration_parity.py.
CONTRADICTION_COLUMNS = {
    "dismissed",
}


def upgrade() -> None:
    op.add_column(
        "contradictions",
        sa.Column(
            "dismissed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.alter_column("contradictions", "dismissed", server_default=None)
    op.create_index(
        "ix_contradictions_user_dismissed",
        "contradictions",
        ["user_id", "dismissed"],
    )


def downgrade() -> None:
    op.drop_index("ix_contradictions_user_dismissed", table_name="contradictions")
    op.drop_column("contradictions", "dismissed")
