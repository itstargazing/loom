"""Per-user local-only domain privacy settings.

Revision ID: 0009_privacy_settings
Revises: 0008_auto_attach
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0009_privacy_settings"
down_revision = "0008_auto_attach"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_privacy_settings",
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column(
            "local_only_domains",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("user_privacy_settings")
