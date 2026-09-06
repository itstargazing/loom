"""Checks that a JSON schema is compatible with provider strict modes.

OpenAI Structured Outputs accepts only a subset of JSON Schema: every object
must set ``additionalProperties: false`` and list all of its properties in
``required``, and keywords like ``minimum`` or ``oneOf`` are rejected outright.

Pydantic emits those unsupported keywords as soon as a model uses
``Field(ge=...)``, ``Field(max_length=...)``, a field default, or a discriminated
union — so this runs as a test over the real schema rather than living only in a
comment.
"""

from typing import Any

#  Keywords a provider strict mode rejects. Constraints belong in Python
#  validators instead, where they do not leak into the schema.
UNSUPPORTED_KEYWORDS = frozenset(
    {
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "multipleOf",
        "minLength",
        "maxLength",
        "pattern",
        "format",
        "minItems",
        "maxItems",
        "uniqueItems",
        "patternProperties",
        "oneOf",
        "allOf",
        "not",
        "default",
        "if",
        "then",
        "else",
    }
)


def strict_schema_violations(schema: dict[str, Any], path: str = "$") -> list[str]:
    """Return a human-readable list of strict-mode violations, empty if valid."""
    problems: list[str] = []

    for keyword in sorted(UNSUPPORTED_KEYWORDS & schema.keys()):
        problems.append(f"{path}: unsupported keyword '{keyword}'")

    if schema.get("type") == "object" or "properties" in schema:
        properties: dict[str, Any] = schema.get("properties", {})

        if schema.get("additionalProperties") is not False:
            problems.append(f"{path}: object must set additionalProperties to false")

        required = set(schema.get("required", []))
        missing = sorted(set(properties) - required)
        if missing:
            problems.append(f"{path}: properties not marked required: {', '.join(missing)}")

        for name, subschema in properties.items():
            problems += strict_schema_violations(subschema, f"{path}.{name}")

    items = schema.get("items")
    if isinstance(items, dict):
        problems += strict_schema_violations(items, f"{path}[]")

    for index, variant in enumerate(schema.get("anyOf", [])):
        problems += strict_schema_violations(variant, f"{path}|anyOf[{index}]")

    for name, definition in schema.get("$defs", {}).items():
        problems += strict_schema_violations(definition, f"$defs.{name}")

    return problems
