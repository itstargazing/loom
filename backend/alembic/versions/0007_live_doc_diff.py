"""Multi-doc live diff watched sets and events.

Revision ID: 0007_live_doc_diff
Revises: 0006_form_filler
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0007_live_doc_diff"
down_revision = "0006_form_filler"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "watched_sets",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("last_viewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_watched_sets_user", "watched_sets", ["user_id"])

    op.create_table(
        "watched_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "set_id",
            sa.Uuid(),
            sa.ForeignKey("watched_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("label", sa.String(512), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_watched_documents_set", "watched_documents", ["set_id"])
    op.create_index(
        "ix_watched_documents_user_url",
        "watched_documents",
        ["user_id", "source_url"],
    )

    op.create_table(
        "document_snapshots",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("watched_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("content_text", sa.Text(), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column(
            "capture_event_id",
            sa.Uuid(),
            sa.ForeignKey("capture_events.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "captured_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index(
        "ix_document_snapshots_document_captured",
        "document_snapshots",
        ["document_id", "captured_at"],
    )

    op.create_table(
        "document_diff_events",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "set_id",
            sa.Uuid(),
            sa.ForeignKey("watched_sets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column(
            "left_document_id",
            sa.Uuid(),
            sa.ForeignKey("watched_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "right_document_id",
            sa.Uuid(),
            sa.ForeignKey("watched_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "left_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("document_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "right_snapshot_id",
            sa.Uuid(),
            sa.ForeignKey("document_snapshots.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("unified_diff", sa.Text(), nullable=False, server_default=""),
        sa.Column("change_summary", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "is_meaningful", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column(
            "detected_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("viewed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_document_diff_events_set_detected",
        "document_diff_events",
        ["set_id", "detected_at"],
    )
    op.create_index(
        "ix_document_diff_events_user_unread",
        "document_diff_events",
        ["user_id", "viewed_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_document_diff_events_user_unread", table_name="document_diff_events"
    )
    op.drop_index(
        "ix_document_diff_events_set_detected", table_name="document_diff_events"
    )
    op.drop_table("document_diff_events")
    op.drop_index(
        "ix_document_snapshots_document_captured", table_name="document_snapshots"
    )
    op.drop_table("document_snapshots")
    op.drop_index("ix_watched_documents_user_url", table_name="watched_documents")
    op.drop_index("ix_watched_documents_set", table_name="watched_documents")
    op.drop_table("watched_documents")
    op.drop_index("ix_watched_sets_user", table_name="watched_sets")
    op.drop_table("watched_sets")
