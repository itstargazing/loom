"""Routing classifications into the typed skill stores.

There is no Postgres here, so the upsert is verified by compiling it against the
PostgreSQL dialect and asserting the SQL says what it should. That catches the
things that actually go wrong — a conflict target that misses the unique
constraint, or a JSONB append that silently overwrites history.
"""

import pytest
from sqlalchemy.dialects import postgresql

from app.models.skill_stores import (
    Citation,
    ContractFlag,
    ContradictionClaim,
    Deadline,
    GlossaryTerm,
    JobListing,
    ProductListing,
    ReadingCompilerEntry,
)
from app.schemas.classification import (
    ClassificationItem,
    ClassificationResult,
    ExtractedFields,
    SkillCategory,
)
from app.services.dedup import dedup_key
from app.services.skill_router import (
    ROUTES,
    RoutingContext,
    build_upsert,
    route_classification,
)

CONTEXT = RoutingContext(
    user_id="dev-user",
    capture_event_id=None,
    source_url="https://example.com/page",
    page_title="A Page",
)


def item(category: SkillCategory, confidence: float = 0.8, **fields) -> ClassificationItem:
    return ClassificationItem(
        category=category,
        confidence=confidence,
        reason="test",
        fields=ExtractedFields.of(**fields),
    )


def compile_sql(statement) -> str:
    return str(
        statement.compile(
            dialect=postgresql.dialect(),
            compile_kwargs={"literal_binds": False},
        )
    )


# --- registry -------------------------------------------------------------


def test_every_category_except_none_has_a_route():
    """A new category without a route would be silently dropped."""
    routable = set(SkillCategory.__args__) - {"none"}
    assert routable == set(ROUTES)


def test_none_has_no_route():
    assert "none" not in ROUTES


@pytest.mark.parametrize(
    "category,model",
    [
        ("glossary_term", GlossaryTerm),
        ("citation", Citation),
        ("deadline", Deadline),
        ("contradiction_candidate", ContradictionClaim),
        ("reading_highlight", ReadingCompilerEntry),
        ("product_listing", ProductListing),
        ("job_listing", JobListing),
        ("contract_clause", ContractFlag),
    ],
)
def test_categories_map_to_their_store(category, model):
    assert ROUTES[category].model is model


# --- dedup identity -------------------------------------------------------


def test_glossary_identity_is_the_term_alone():
    """The same term on a different page is one entry with two sightings."""
    route = ROUTES["glossary_term"]
    fields = ExtractedFields.of(term="idempotent", definition="safe to repeat")

    elsewhere = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://other.example.com/x",
        page_title="Somewhere Else",
    )

    assert route.key(fields, CONTEXT) == route.key(fields, elsewhere)


def test_deadline_identity_includes_the_source_document():
    """Two courses can share 'Problem Set 3' on one date and still differ."""
    route = ROUTES["deadline"]
    fields = ExtractedFields.of(
        deadline_title="Problem Set 3", deadline_date="2026-09-15"
    )

    other_course = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://university.edu/cs202/syllabus",
        page_title="CS202",
    )

    assert route.key(fields, CONTEXT) != route.key(fields, other_course)


def test_deadline_identity_merges_filename_versions_of_the_same_doc():
    route = ROUTES["deadline"]
    fields = ExtractedFields.of(
        deadline_title="Problem Set 3", deadline_date="2026-09-15"
    )
    pdf = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://university.edu/cs101/syllabus.pdf",
        page_title="CS101",
    )
    revision = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://university.edu/cs101/syllabus-v2.pdf",
        page_title="CS101",
    )
    assert route.key(fields, pdf) == route.key(fields, revision)


def test_deadline_columns_resolve_the_date_and_stay_unconfirmed_when_guessy():
    context = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://university.edu/cs101/syllabus",
        page_title="CS101 Syllabus",
        context_text="Problem Set 3 is due 2026-09-15.",
        occurred_at="2026-08-28T10:00:00+00:00",
    )
    columns = ROUTES["deadline"].columns(
        ExtractedFields.of(
            deadline_title="Problem Set 3",
            deadline_date="2026-09-15",
            deadline_kind="assignment_due",
        ),
        context,
    )
    assert columns["due_date"].date().isoformat() == "2026-09-15"
    assert columns["context_snippet"] == context.context_text
    assert columns["confirmed"] is False

    high = item(
        "deadline",
        0.8,
        deadline_title="Problem Set 3",
        deadline_date="2026-09-15",
        deadline_kind="assignment_due",
    )
    values = build_upsert(ROUTES["deadline"], high, context).compile(
        dialect=postgresql.dialect()
    ).params
    assert values["confirmed"] is True


def test_claim_identity_includes_the_source():
    """Contradiction detection depends on keeping per-source claims apart."""
    route = ROUTES["contradiction_candidate"]
    fields = ExtractedFields.of(claim="Temperatures rose 1.2C", topic="climate")

    other_source = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://other.example.com/report",
        page_title="Another Report",
    )

    assert route.key(fields, CONTEXT) != route.key(fields, other_source)


def test_citation_identity_ignores_the_source_url():
    """One passage reached via two URLs is a single citation."""
    route = ROUTES["citation"]
    fields = ExtractedFields.of(quote="A quotable sentence.")

    mirror = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://mirror.example.com/same",
        page_title="Mirror",
    )

    assert route.key(fields, CONTEXT) == route.key(fields, mirror)


# --- generated SQL --------------------------------------------------------


def test_upsert_targets_the_dedup_unique_constraint():
    statement = build_upsert(
        ROUTES["glossary_term"],
        item("glossary_term", term="attention", definition="a weighting"),
        CONTEXT,
    )
    sql = compile_sql(statement)

    assert "INSERT INTO glossary_terms" in sql
    assert "ON CONFLICT (user_id, dedup_key) DO UPDATE" in sql


def test_upsert_increments_rather_than_resetting_times_seen():
    statement = build_upsert(
        ROUTES["citation"], item("citation", quote="A sentence."), CONTEXT
    )
    sql = compile_sql(statement)

    assert "times_seen = (citations.times_seen + " in sql, sql


def test_upsert_appends_to_occurrences_instead_of_replacing_them():
    """`||` on jsonb concatenates; assignment would discard sighting history."""
    statement = build_upsert(
        ROUTES["citation"], item("citation", quote="A sentence."), CONTEXT
    )
    sql = compile_sql(statement)

    assert "occurrences = (citations.occurrences || CAST" in sql, sql
    assert "AS JSONB)" in sql, sql


def test_upsert_keeps_the_highest_confidence():
    statement = build_upsert(
        ROUTES["citation"], item("citation", quote="A sentence."), CONTEXT
    )
    sql = compile_sql(statement)

    assert "greatest(citations.confidence" in sql


def test_upsert_returns_times_seen_to_distinguish_insert_from_merge():
    statement = build_upsert(
        ROUTES["citation"], item("citation", quote="A sentence."), CONTEXT
    )
    sql = compile_sql(statement)

    assert "RETURNING citations.id, citations.times_seen" in sql


def test_upsert_values_include_the_expected_dedup_key():
    entry = item("glossary_term", term="Attention", definition="a weighting")
    statement = build_upsert(ROUTES["glossary_term"], entry, CONTEXT)

    values = statement.compile(dialect=postgresql.dialect()).params
    assert values["dedup_key"] == dedup_key("Attention")
    assert values["user_id"] == "dev-user"
    assert values["times_seen"] == 1
    assert values["context_snippet"] == ""


def test_glossary_context_snippet_comes_from_the_capture_payload():
    """The model extracts term+definition; the surrounding paragraph is ours."""
    context = RoutingContext(
        user_id="dev-user",
        capture_event_id=None,
        source_url="https://example.com/page",
        page_title="A Page",
        context_text="We inject positional encoding so the model knows token order.",
    )
    statement = build_upsert(
        ROUTES["glossary_term"],
        item("glossary_term", term="positional encoding", definition="order signal"),
        context,
    )
    values = statement.compile(dialect=postgresql.dialect()).params
    assert values["context_snippet"] == context.context_text


def test_citation_upsert_stores_apa_and_mla():
    statement = build_upsert(
        ROUTES["citation"],
        item(
            "citation",
            quote="Temperatures rose 1.2C.",
            author="Jane Hansen",
            work_title="Global temperature trends",
            publisher="Nature",
            published_date="2024",
        ),
        CONTEXT,
    )
    values = statement.compile(dialect=postgresql.dialect()).params
    formatted = values["formatted"]
    assert set(formatted) == {"apa", "mla"}
    assert "Hansen, J. (2024)." in formatted["apa"]
    assert '"Global temperature trends."' in formatted["mla"]


def test_citation_falls_back_to_page_title_when_work_title_is_missing():
    columns = ROUTES["citation"].columns(
        ExtractedFields.of(quote="A quotable sentence."), CONTEXT
    )
    assert columns["work_title"] == CONTEXT.page_title
    assert CONTEXT.page_title in columns["formatted"]["apa"]


def test_product_specs_are_flattened_to_a_mapping():
    from app.schemas.classification import SpecField

    entry = ClassificationItem(
        category="product_listing",
        confidence=0.7,
        reason="test",
        fields=ExtractedFields.of(
            product_name="Widget",
            specs=[SpecField(name="Weight", value="1kg"), SpecField(name="Color", value="Black")],
        ),
    )
    columns = ROUTES["product_listing"].columns(entry.fields, CONTEXT)

    assert columns["specs"] == {"Weight": "1kg", "Color": "Black"}


def test_job_requirements_default_to_an_empty_list():
    entry = item("job_listing", job_title="Engineer")
    assert ROUTES["job_listing"].columns(entry.fields, CONTEXT)["requirements"] == []


# --- routing a whole result ----------------------------------------------


class FakeResult:
    def __init__(self, row):
        self._row = row

    def one(self):
        return self._row


class FakeSession:
    """Records executed statements and reports every row as a fresh insert."""

    def __init__(self, times_seen: int = 1):
        self.statements = []
        self.commits = 0
        self._times_seen = times_seen

    async def execute(self, statement):
        self.statements.append(statement)
        from uuid import uuid4

        return FakeResult((uuid4(), self._times_seen))

    async def commit(self):
        self.commits += 1


async def test_multi_classification_writes_to_every_store():
    result = ClassificationResult(
        classifications=[
            item("glossary_term", term="attention", definition="a weighting"),
            item("reading_highlight", passage="Attention is all you need."),
        ]
    )
    session = FakeSession()

    outcome = await route_classification(session, result, CONTEXT)

    assert len(outcome.entries) == 2
    assert {entry.table for entry in outcome.entries} == {
        "glossary_terms",
        "reading_compiler_entries",
    }
    assert outcome.created_count == 2
    assert session.commits == 1


async def test_none_is_skipped_not_written():
    result = ClassificationResult(classifications=[item("none", confidence=0.9)])
    session = FakeSession()

    outcome = await route_classification(session, result, CONTEXT)

    assert outcome.entries == []
    assert outcome.skipped == ["none"]
    assert session.statements == []


async def test_repeat_sighting_counts_as_merged_not_created():
    result = ClassificationResult(
        classifications=[item("glossary_term", term="attention", definition="a weighting")]
    )
    # times_seen of 2 is what Postgres returns when the upsert hit a conflict.
    session = FakeSession(times_seen=2)

    outcome = await route_classification(session, result, CONTEXT)

    assert outcome.created_count == 0
    assert outcome.merged_count == 1


async def test_routing_commits_once_for_the_whole_result():
    """All-or-nothing: an event lands in every store or none of them."""
    result = ClassificationResult(
        classifications=[
            item("glossary_term", term="a", definition="b"),
            item("citation", quote="A sentence."),
            item("reading_highlight", passage="A passage."),
        ]
    )
    session = FakeSession()

    await route_classification(session, result, CONTEXT)

    assert len(session.statements) == 3
    assert session.commits == 1
