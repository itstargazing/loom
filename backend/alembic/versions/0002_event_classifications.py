"""Create event_classifications table.

Revision ID: 0002_event_classifications
Revises: 0001_capture_events
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0002_event_classifications"
down_revision = "0001_capture_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "event_classifications",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("capture_event_id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("categories", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("raw_output", sa.Text(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["capture_event_id"], ["capture_events.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
        # One row per event: reprocessing under at-least-once delivery updates
        # in place rather than accumulating duplicates.
        sa.UniqueConstraint("capture_event_id", name="uq_event_classifications_event"),
    )
    op.create_index(
        "ix_event_classifications_user_created",
        "event_classifications",
        ["user_id", "created_at"],
    )
    op.create_index(
        "ix_event_classifications_status", "event_classifications", ["status"]
    )
    op.create_index(
        "ix_event_classifications_categories",
        "event_classifications",
        ["categories"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    op.drop_index("ix_event_classifications_categories", table_name="event_classifications")
    op.drop_index("ix_event_classifications_status", table_name="event_classifications")
    op.drop_index(
        "ix_event_classifications_user_created", table_name="event_classifications"
    )
    op.drop_table("event_classifications")
