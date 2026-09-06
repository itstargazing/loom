"""The classification schema is a contract with the model provider.

The strict-mode test is the important one: if someone adds a field default or a
``Field(ge=...)`` constraint, the schema silently stops being acceptable to
Structured Outputs and every classification would fail at runtime instead.
"""

import pytest
from pydantic import ValidationError

from app.ai.schema_utils import strict_schema_violations
from app.schemas.classification import (
    REQUIRED_FIELDS,
    ClassificationItem,
    ClassificationResult,
    ExtractedFields,
    SkillCategory,
    classification_json_schema,
)


def test_schema_is_strict_mode_compatible():
    violations = strict_schema_violations(classification_json_schema())
    assert violations == [], "\n".join(violations)


def test_every_category_has_a_required_fields_entry():
    declared = set(SkillCategory.__args__)
    assert declared == set(REQUIRED_FIELDS), "REQUIRED_FIELDS is out of sync"


def test_required_field_names_exist_on_extracted_fields():
    known = set(ExtractedFields.model_fields)
    for category, names in REQUIRED_FIELDS.items():
        unknown = set(names) - known
        assert not unknown, f"{category} references unknown fields: {unknown}"


def test_missing_required_field_is_rejected():
    with pytest.raises(ValidationError, match="requires non-empty fields"):
        ClassificationItem(
            category="glossary_term",
            confidence=0.9,
            reason="looks like a term",
            # definition is mandatory for glossary_term
            fields=ExtractedFields.of(term="idempotent"),
        )


def test_empty_string_counts_as_missing():
    with pytest.raises(ValidationError, match="requires non-empty fields"):
        ClassificationItem(
            category="citation",
            confidence=0.8,
            reason="quotable",
            fields=ExtractedFields.of(quote=""),
        )


def test_none_category_needs_no_fields():
    item = ClassificationItem(
        category="none",
        confidence=0.9,
        reason="navigation chrome",
        fields=ExtractedFields.of(),
    )
    assert item.fields.present() == {}


def test_confidence_is_clamped():
    item = ClassificationItem(
        category="none", confidence=4.2, reason="over", fields=ExtractedFields.of()
    )
    assert item.confidence == 1.0

    item = ClassificationItem(
        category="none", confidence=-1.0, reason="under", fields=ExtractedFields.of()
    )
    assert item.confidence == 0.0


def test_none_cannot_be_combined_with_another_category():
    with pytest.raises(ValidationError, match="cannot be combined"):
        ClassificationResult(
            classifications=[
                ClassificationItem(
                    category="none",
                    confidence=0.5,
                    reason="nothing",
                    fields=ExtractedFields.of(),
                ),
                ClassificationItem(
                    category="reading_highlight",
                    confidence=0.5,
                    reason="a passage",
                    fields=ExtractedFields.of(passage="something worth keeping"),
                ),
            ]
        )


def test_duplicate_categories_are_rejected():
    def highlight(passage: str) -> ClassificationItem:
        return ClassificationItem(
            category="reading_highlight",
            confidence=0.6,
            reason="a passage",
            fields=ExtractedFields.of(passage=passage),
        )

    with pytest.raises(ValidationError, match="duplicate categories"):
        ClassificationResult(classifications=[highlight("first"), highlight("second")])


def test_multi_classification_is_allowed():
    result = ClassificationResult(
        classifications=[
            ClassificationItem(
                category="glossary_term",
                confidence=0.8,
                reason="technical term",
                fields=ExtractedFields.of(term="attention", definition="a weighting"),
            ),
            ClassificationItem(
                category="reading_highlight",
                confidence=0.7,
                reason="worth rereading",
                fields=ExtractedFields.of(passage="Attention is all you need."),
            ),
        ]
    )

    assert result.categories == ["glossary_term", "reading_highlight"]
    assert not result.is_none


def test_extra_fields_are_rejected():
    with pytest.raises(ValidationError):
        ExtractedFields.of(term="x", definition="y", invented_field="z")


def test_present_omits_nulls_and_empty_lists():
    fields = ExtractedFields.of(job_title="Engineer", requirements=[])
    assert fields.present() == {"job_title": "Engineer"}
