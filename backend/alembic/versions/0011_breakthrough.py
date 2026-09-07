"""Breakthrough features: review state, embeddings, briefs, nudges.

Revision ID: 0011_breakthrough
Revises: 0010_user_accounts
Create Date: 2026-09-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0011_breakthrough"
down_revision = "0010_user_accounts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("capture_events", sa.Column("referring_url", sa.Text(), nullable=True))
    op.add_column(
        "event_classifications",
        sa.Column("cached", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "event_classifications",
        sa.Column("max_confidence", sa.Float(), nullable=False, server_default="0"),
    )
    op.add_column(
        "event_classifications",
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "event_classifications",
        sa.Column(
            "review_status",
            sa.String(32),
            nullable=False,
            server_default="auto_routed",
        ),
    )
    op.add_column(
        "contradictions",
        sa.Column("agree_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "contradictions",
        sa.Column("disagree_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "contradictions",
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )

    op.create_table(
        "classification_corrections",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column(
            "capture_event_id",
            sa.Uuid(),
            sa.ForeignKey("capture_events.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("original_categories", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("corrected_category", sa.String(64), nullable=False),
        sa.Column("action", sa.String(32), nullable=False),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_classification_corrections_user",
        "classification_corrections",
        ["user_id", "created_at"],
    )

    op.create_table(
        "capture_embeddings",
        sa.Column(
            "capture_event_id",
            sa.Uuid(),
            sa.ForeignKey("capture_events.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("embedding", postgresql.ARRAY(sa.Float()), nullable=False),
        sa.Column("model", sa.String(128), nullable=False, server_default=""),
        sa.Column("snippet", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_capture_embeddings_user", "capture_embeddings", ["user_id"])

    op.create_table(
        "research_briefs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("topic", sa.Text(), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=False),
        sa.Column("source_event_ids", postgresql.ARRAY(sa.Text()), nullable=False),
        sa.Column("deadline_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_research_briefs_user", "research_briefs", ["user_id", "created_at"])

    op.create_table(
        "dashboard_notifications",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("kind", sa.String(64), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("href", sa.Text(), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dismissed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_dashboard_notifications_user",
        "dashboard_notifications",
        ["user_id", "created_at"],
    )

    op.create_table(
        "deadline_nudge_log",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("deadline_id", sa.Uuid(), nullable=False),
        sa.Column("day", sa.String(10), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "deadline_id", "day", name="uq_deadline_nudge_day"),
    )

    op.execute(
        """
        DO $$ BEGIN
            CREATE EXTENSION IF NOT EXISTS vector;
        EXCEPTION WHEN OTHERS THEN
            NULL;
        END $$;
        """
    )


def downgrade() -> None:
    op.drop_table("deadline_nudge_log")
    op.drop_table("dashboard_notifications")
    op.drop_table("research_briefs")
    op.drop_table("capture_embeddings")
    op.drop_table("classification_corrections")
    op.drop_column("contradictions", "evidence")
    op.drop_column("contradictions", "disagree_count")
    op.drop_column("contradictions", "agree_count")
    op.drop_column("event_classifications", "review_status")
    op.drop_column("event_classifications", "snippet")
    op.drop_column("event_classifications", "max_confidence")
    op.drop_column("event_classifications", "cached")
    op.drop_column("capture_events", "referring_url")
