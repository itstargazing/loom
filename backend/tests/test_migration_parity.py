"""Guards against model/migration drift.

Alembic's autogenerate diff needs a live database, which these tests do not
have. The migration declares its skill-store columns as data, so the same
information can be compared against the mapped models directly — which catches
the common mistake of adding a column to a model and forgetting the migration.
"""

import importlib.util
from pathlib import Path
from types import ModuleType

from app.core.database import Base
from app.models.skill_stores import SkillEntry

MIGRATIONS = Path(__file__).resolve().parent.parent / "alembic" / "versions"


def load_migration(filename: str) -> ModuleType:
    """Load a revision by path.

    Revision filenames start with a digit and ``alembic.versions`` is not a
    package, so neither is importable by name.
    """
    spec = importlib.util.spec_from_file_location(
        filename.removesuffix(".py"), MIGRATIONS / filename
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


migration = load_migration("0003_skill_stores.py")
later = load_migration("0004_deadline_calendar.py")
contradiction_later = load_migration("0005_contradiction_dismiss.py")

#  Present on every table but declared outside SKILL_TABLES/SHARED_COLUMNS.
TIMESTAMP_COLUMNS = {"created_at", "last_seen_at"}
ADDED_COLUMNS = {"deadlines": later.DEADLINE_COLUMNS}


def migration_columns(table: str) -> set[str]:
    shared = {name for name, _type, _kwargs in migration.SHARED_COLUMNS}
    specific = {column.name for column in migration.SKILL_TABLES[table]}
    return shared | specific | TIMESTAMP_COLUMNS | ADDED_COLUMNS.get(table, set())


def model_columns(table: str) -> set[str]:
    return {column.name for column in Base.metadata.tables[table].columns}


def test_every_skill_store_model_has_a_migration():
    skill_models = {
        mapper.class_.__tablename__
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, SkillEntry)
    }
    assert skill_models == set(migration.SKILL_TABLES)


def test_skill_store_columns_match_the_migration():
    mismatches = {}
    for table in migration.SKILL_TABLES:
        expected = migration_columns(table)
        actual = model_columns(table)
        if expected != actual:
            mismatches[table] = {
                "only_in_migration": sorted(expected - actual),
                "only_in_model": sorted(actual - expected),
            }

    assert mismatches == {}


def test_shared_envelope_is_declared_once():
    """Every skill store must carry the full SkillEntry envelope."""
    shared = {name for name, _type, _kwargs in migration.SHARED_COLUMNS}

    for table in migration.SKILL_TABLES:
        missing = shared - model_columns(table)
        assert not missing, f"{table} is missing {sorted(missing)}"


def test_dedup_key_width_matches_the_migration():
    """A shorter column than the key would truncate and cause false merges."""
    declared = dict(
        (name, type_) for name, type_, _kwargs in migration.SHARED_COLUMNS
    )["dedup_key"]

    from app.models.skill_stores import DEDUP_KEY_LENGTH

    assert declared.length == DEDUP_KEY_LENGTH


def test_routed_at_exists_on_event_classifications():
    assert "routed_at" in model_columns("event_classifications")


def test_contradiction_dismiss_column_matches_migration():
    expected = contradiction_later.CONTRADICTION_COLUMNS
    actual = model_columns("contradictions")
    assert expected <= actual
    assert "dismissed" in actual


form_later = load_migration("0006_form_filler.py")
live_doc_later = load_migration("0007_live_doc_diff.py")
auto_attach_later = load_migration("0008_auto_attach.py")
privacy_later = load_migration("0009_privacy_settings.py")
account_later = load_migration("0010_user_accounts.py")


def test_form_filler_tables_match_models():
    assert "form_profiles" in Base.metadata.tables
    assert "form_documents" in Base.metadata.tables
    assert form_later.revision == "0006_form_filler"
    assert {
        "id",
        "user_id",
        "name",
        "values",
        "created_at",
        "updated_at",
    } <= model_columns("form_profiles")
    assert {
        "id",
        "user_id",
        "filename",
        "storage_path",
        "source_url",
        "fields",
        "field_count",
        "created_at",
    } <= model_columns("form_documents")


def test_live_doc_diff_tables_match_models():
    assert live_doc_later.revision == "0007_live_doc_diff"
    assert live_doc_later.down_revision == "0006_form_filler"
    for table in (
        "watched_sets",
        "watched_documents",
        "document_snapshots",
        "document_diff_events",
    ):
        assert table in Base.metadata.tables
    assert {
        "id",
        "user_id",
        "name",
        "created_at",
        "last_viewed_at",
    } <= model_columns("watched_sets")
    assert {
        "id",
        "set_id",
        "user_id",
        "label",
        "source_url",
        "created_at",
    } <= model_columns("watched_documents")
    assert {
        "id",
        "document_id",
        "user_id",
        "content_text",
        "content_hash",
        "capture_event_id",
        "captured_at",
    } <= model_columns("document_snapshots")
    assert {
        "id",
        "set_id",
        "user_id",
        "left_document_id",
        "right_document_id",
        "left_snapshot_id",
        "right_snapshot_id",
        "unified_diff",
        "change_summary",
        "is_meaningful",
        "detected_at",
        "viewed_at",
    } <= model_columns("document_diff_events")


def test_auto_attach_tables_match_models():
    assert auto_attach_later.revision == "0008_auto_attach"
    assert auto_attach_later.down_revision == "0007_live_doc_diff"
    assert "recent_documents" in Base.metadata.tables
    assert {
        "id",
        "user_id",
        "filename",
        "source_url",
        "doc_type",
        "summary",
        "mime_type",
        "storage_path",
        "created_at",
        "last_seen_at",
    } <= model_columns("recent_documents")


def test_privacy_settings_table_matches_model():
    assert privacy_later.revision == "0009_privacy_settings"
    assert privacy_later.down_revision == "0008_auto_attach"
    assert "user_privacy_settings" in Base.metadata.tables
    assert {
        "user_id",
        "local_only_domains",
        "updated_at",
        "notes",
    } <= model_columns("user_privacy_settings")


def test_user_accounts_table_matches_model():
    assert account_later.revision == "0010_user_accounts"
    assert account_later.down_revision == "0009_privacy_settings"
    assert "user_accounts" in Base.metadata.tables
    assert {
        "user_id",
        "display_name",
        "email",
        "auth_mode",
        "created_at",
        "updated_at",
        "notes",
    } <= model_columns("user_accounts")
