"""Recent documents index for Smart File Auto-Attach.

Revision ID: 0008_auto_attach
Revises: 0007_live_doc_diff
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0008_auto_attach"
down_revision = "0007_live_doc_diff"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "recent_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False, server_default=""),
        sa.Column("doc_type", sa.String(64), nullable=False, server_default="other"),
        sa.Column("summary", sa.Text(), nullable=False, server_default=""),
        sa.Column("mime_type", sa.String(128), nullable=False, server_default=""),
        sa.Column("storage_path", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id",
            "source_url",
            "filename",
            name="uq_recent_documents_user_url_name",
        ),
    )
    op.create_index(
        "ix_recent_documents_user_seen",
        "recent_documents",
        ["user_id", "last_seen_at"],
    )


def downgrade() -> None:
    op.drop_index("ix_recent_documents_user_seen", table_name="recent_documents")
    op.drop_table("recent_documents")
