"""Create capture_events table.

Revision ID: 0001_capture_events
Revises:
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0001_capture_events"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "capture_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("page_title", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "received_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_capture_events_user_occurred", "capture_events", ["user_id", "occurred_at"]
    )
    op.create_index(
        "ix_capture_events_user_type", "capture_events", ["user_id", "event_type"]
    )


def downgrade() -> None:
    op.drop_index("ix_capture_events_user_type", table_name="capture_events")
    op.drop_index("ix_capture_events_user_occurred", table_name="capture_events")
    op.drop_table("capture_events")
