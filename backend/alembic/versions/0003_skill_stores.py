"""Create collections and the typed skill stores.

Revision ID: 0003_skill_stores
Revises: 0002_event_classifications
Create Date: 2026-08-28
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "0003_skill_stores"
down_revision = "0002_event_classifications"
branch_labels = None
depends_on = None

#  Columns shared by every skill store, mirroring the SkillEntry mixin.
SHARED_COLUMNS = (
    ("id", sa.Uuid(), {"nullable": False}),
    ("user_id", sa.String(length=255), {"nullable": False}),
    ("capture_event_id", sa.Uuid(), {"nullable": True}),
    ("collection_id", sa.Uuid(), {"nullable": True}),
    ("dedup_key", sa.String(length=32), {"nullable": False}),
    ("source_url", sa.Text(), {"nullable": False}),
    ("page_title", sa.Text(), {"nullable": False}),
    ("confidence", sa.Float(), {"nullable": False}),
    ("times_seen", sa.Integer(), {"nullable": False}),
    ("occurrences", postgresql.JSONB(astext_type=sa.Text()), {"nullable": False}),
)

SKILL_TABLES = {
    "glossary_terms": [
        sa.Column("term", sa.Text(), nullable=False),
        sa.Column("definition", sa.Text(), nullable=False),
        sa.Column("context_snippet", sa.Text(), nullable=False),
    ],
    "citations": [
        sa.Column("quote", sa.Text(), nullable=False),
        sa.Column("author", sa.Text(), nullable=True),
        sa.Column("work_title", sa.Text(), nullable=True),
        sa.Column("publisher", sa.Text(), nullable=True),
        sa.Column("published_date", sa.String(length=64), nullable=True),
        sa.Column(
            "formatted", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
    ],
    "deadlines": [
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("due_text", sa.String(length=255), nullable=False),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=True),
    ],
    "contradiction_claims": [
        sa.Column("claim", sa.Text(), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
    ],
    "reading_compiler_entries": [
        sa.Column("passage", sa.Text(), nullable=False),
        sa.Column("dwell_ms", sa.Integer(), nullable=False),
        sa.Column("heading", sa.Text(), nullable=True),
    ],
    "product_listings": [
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("price", sa.String(length=64), nullable=True),
        sa.Column("specs", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    ],
    "job_listings": [
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("company", sa.Text(), nullable=True),
        sa.Column("salary", sa.String(length=128), nullable=True),
        sa.Column(
            "requirements", postgresql.JSONB(astext_type=sa.Text()), nullable=False
        ),
        sa.Column("application_deadline", sa.String(length=255), nullable=True),
    ],
    "contract_flags": [
        sa.Column("clause_text", sa.Text(), nullable=False),
        sa.Column("flag_reason", sa.Text(), nullable=False),
        sa.Column("risk_level", sa.String(length=16), nullable=False),
    ],
}


def _shared_columns() -> list[sa.Column]:
    return [sa.Column(name, type_, **kwargs) for name, type_, kwargs in SHARED_COLUMNS]


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "name", name="uq_collections_user_name"),
    )
    op.create_index("ix_collections_user_id", "collections", ["user_id"])

    for table, skill_columns in SKILL_TABLES.items():
        op.create_table(
            table,
            *_shared_columns(),
            *skill_columns,
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "last_seen_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.PrimaryKeyConstraint("id"),
            # SET NULL, not CASCADE: purging raw capture history must not erase
            # the structured output derived from it.
            sa.ForeignKeyConstraint(
                ["capture_event_id"], ["capture_events.id"], ondelete="SET NULL"
            ),
            sa.ForeignKeyConstraint(
                ["collection_id"], ["collections.id"], ondelete="SET NULL"
            ),
            # Entry identity, and the target of the router's upserts.
            sa.UniqueConstraint(
                "user_id", "dedup_key", name=f"uq_{table}_user_dedup"
            ),
        )
        op.create_index(f"ix_{table}_user_created", table, ["user_id", "created_at"])
        op.create_index(f"ix_{table}_collection", table, ["collection_id"])

    op.create_index(
        "ix_contradiction_claims_topic", "contradiction_claims", ["topic"]
    )

    op.create_table(
        "contradictions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=255), nullable=False),
        sa.Column("claim_a", sa.Text(), nullable=False),
        sa.Column("claim_b", sa.Text(), nullable=False),
        sa.Column("source_a_url", sa.Text(), nullable=False),
        sa.Column("source_b_url", sa.Text(), nullable=False),
        sa.Column("explanation", sa.Text(), nullable=False),
        sa.Column("claim_a_id", sa.Uuid(), nullable=True),
        sa.Column("claim_b_id", sa.Uuid(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["claim_a_id"], ["contradiction_claims.id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["claim_b_id"], ["contradiction_claims.id"], ondelete="SET NULL"
        ),
        sa.UniqueConstraint(
            "user_id", "claim_a_id", "claim_b_id", name="uq_contradictions_pair"
        ),
    )
    op.create_index(
        "ix_contradictions_user_created", "contradictions", ["user_id", "created_at"]
    )

    op.add_column(
        "event_classifications",
        sa.Column("routed_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("event_classifications", "routed_at")

    op.drop_index("ix_contradictions_user_created", table_name="contradictions")
    op.drop_table("contradictions")

    op.drop_index("ix_contradiction_claims_topic", table_name="contradiction_claims")

    for table in reversed(list(SKILL_TABLES)):
        op.drop_index(f"ix_{table}_collection", table_name=table)
        op.drop_index(f"ix_{table}_user_created", table_name=table)
        op.drop_table(table)

    op.drop_index("ix_collections_user_id", table_name="collections")
    op.drop_table("collections")
