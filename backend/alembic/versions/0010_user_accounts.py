"""User account profiles for Phase 15 auth scaffolding.

Revision ID: 0010_user_accounts
Revises: 0009_privacy_settings
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op

revision = "0010_user_accounts"
down_revision = "0009_privacy_settings"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_accounts",
        sa.Column("user_id", sa.String(255), primary_key=True),
        sa.Column("display_name", sa.String(255), nullable=False, server_default=""),
        sa.Column("email", sa.String(320), nullable=True),
        sa.Column("auth_mode", sa.String(32), nullable=False, server_default="stub"),
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
        sa.Column("notes", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("user_accounts")
