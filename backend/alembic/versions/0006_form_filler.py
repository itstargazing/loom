"""Form filler profiles and uploaded PDF documents.

Revision ID: 0006_form_filler
Revises: 0005_contradiction_dismiss
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0006_form_filler"
down_revision = "0005_contradiction_dismiss"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "form_profiles",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column(
            "values",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("user_id", "name", name="uq_form_profiles_user_name"),
    )
    op.create_index("ix_form_profiles_user", "form_profiles", ["user_id"])

    op.create_table(
        "form_documents",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.String(255), nullable=False),
        sa.Column("filename", sa.String(512), nullable=False),
        sa.Column("storage_path", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "fields",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("field_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_form_documents_user_created", "form_documents", ["user_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_form_documents_user_created", table_name="form_documents")
    op.drop_table("form_documents")
    op.drop_index("ix_form_profiles_user", table_name="form_profiles")
    op.drop_table("form_profiles")
