"""The strict-schema checker itself, so its guarantees are trustworthy."""

from app.ai.schema_utils import strict_schema_violations

VALID = {
    "type": "object",
    "additionalProperties": False,
    "required": ["name"],
    "properties": {"name": {"type": "string"}},
}


def test_valid_schema_has_no_violations():
    assert strict_schema_violations(VALID) == []


def test_missing_additional_properties_is_flagged():
    schema = {**VALID}
    del schema["additionalProperties"]

    violations = strict_schema_violations(schema)
    assert any("additionalProperties" in problem for problem in violations)


def test_optional_property_is_flagged():
    schema = {**VALID, "required": []}

    violations = strict_schema_violations(schema)
    assert any("not marked required" in problem for problem in violations)


def test_unsupported_keyword_is_flagged_with_its_path():
    schema = {
        **VALID,
        "properties": {"name": {"type": "number", "minimum": 0}},
    }

    violations = strict_schema_violations(schema)
    assert violations == ["$.name: unsupported keyword 'minimum'"]


def test_nested_defs_are_checked():
    schema = {
        **VALID,
        "$defs": {"Inner": {"type": "object", "properties": {"a": {"type": "string"}}}},
    }

    violations = strict_schema_violations(schema)
    assert any("$defs.Inner" in problem for problem in violations)


def test_array_items_are_checked():
    schema = {
        **VALID,
        "properties": {
            "name": {
                "type": "array",
                "items": {"type": "object", "properties": {"a": {"type": "string"}}},
            }
        },
    }

    violations = strict_schema_violations(schema)
    assert any("$.name[]" in problem for problem in violations)


def test_any_of_branches_are_checked():
    schema = {
        **VALID,
        "properties": {
            "name": {
                "anyOf": [
                    {"type": "object", "properties": {"a": {"type": "string"}}},
                    {"type": "null"},
                ]
            }
        },
    }

    violations = strict_schema_violations(schema)
    assert any("anyOf[0]" in problem for problem in violations)


def test_one_of_is_rejected():
    """Pydantic emits oneOf for discriminated unions, which strict mode rejects."""
    schema = {**VALID, "oneOf": [{"type": "string"}]}
    assert any("oneOf" in problem for problem in strict_schema_violations(schema))
