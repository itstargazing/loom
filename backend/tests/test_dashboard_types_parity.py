"""Guards the dashboard's hand-written types against the backend's OpenAPI schema.

The dashboard declares its own interfaces in ``dashboard/src/lib/types.ts`` so it
can be read and built without a codegen step. That only stays safe if something
fails when a field is renamed on one side and not the other, which is what this
test does. It parses the TypeScript by hand — the file is a flat list of plain
interfaces, deliberately kept that way so this stays a few lines of regex.
"""

import re
from pathlib import Path

import pytest

from app.main import app

TYPES_FILE = Path(__file__).resolve().parents[2] / "dashboard" / "src" / "lib" / "types.ts"

#  OpenAPI component name -> dashboard interface name. The backend suffixes its
#  read models with "Out"; the dashboard has no input models to distinguish from.
SCHEMA_TO_INTERFACE = {
    "DashboardOverview": "DashboardOverview",
    "ActivityItem": "ActivityItem",
    "CaptureSummary": "CaptureSummary",
    "ClassificationSummary": "ClassificationSummary",
    "SkillCount": "SkillCount",
    "GlossaryTermOut": "GlossaryTerm",
    "CitationOut": "Citation",
    "DeadlineOut": "Deadline",
    "ContradictionClaimOut": "ContradictionClaim",
    "ContradictionOut": "Contradiction",
    "ReadingCompilerEntryOut": "ReadingCompilerEntry",
    "ProductListingOut": "ProductListing",
    "JobListingOut": "JobListing",
    "ContractFlagOut": "ContractFlag",
    "CollectionOut": "Collection",
    "FormProfileOut": "FormProfile",
    "FormDocumentOut": "FormDocument",
    "FormFieldOut": "FormField",
    "FieldMatchOut": "FieldMatch",
    "DocumentMatchOut": "DocumentMatch",
    "NormalizedPriceOut": "NormalizedPrice",
    "ProductCompareColumnOut": "ProductCompareColumn",
    "ProductCompareOut": "ProductCompare",
    "WatchedDocumentOut": "WatchedDocument",
    "DocumentDiffEventOut": "DocumentDiffEvent",
    "WatchedSetOut": "WatchedSet",
    "WatchedSetDetailOut": "WatchedSetDetail",
    "UnreadCountOut": "UnreadCount",
    "RecentDocumentOut": "RecentDocument",
    "AutoAttachMatchOut": "AutoAttachMatch",
    "PrivacySettingsOut": "PrivacySettings",
    "LocalModeCheckOut": "LocalModeCheck",
    "AccountOut": "Account",
    "LogoutOut": "LogoutResult",
}

#  Backend read models the dashboard does not surface yet. Listing them means a
#  newly added model fails this test until it is either given a dashboard type or
#  consciously deferred here.
NOT_YET_ON_DASHBOARD = {
    "CaptureEventOut",
    "EventClassificationOut",
    #  Compile preview is consumed inline by the reading page, not typed in types.ts.
    "ReadingCompileOut",
    "ReadingCompilePassageOut",
}

INTERFACE_RE = re.compile(
    r"^export interface (?P<name>\w+)(?: extends (?P<base>\w+))? \{(?P<body>.*?)^\}",
    re.MULTILINE | re.DOTALL,
)
FIELD_RE = re.compile(r"^\s{2}(?P<name>\w+)\??:", re.MULTILINE)


def parse_interfaces(source: str) -> dict[str, tuple[str | None, set[str]]]:
    return {
        match.group("name"): (
            match.group("base"),
            set(FIELD_RE.findall(match.group("body"))),
        )
        for match in INTERFACE_RE.finditer(source)
    }


@pytest.fixture(scope="module")
def dashboard_interfaces() -> dict[str, set[str]]:
    """Every interface's fields, with inherited fields folded in."""
    parsed = parse_interfaces(TYPES_FILE.read_text(encoding="utf-8"))

    def fields(name: str) -> set[str]:
        base, own = parsed[name]
        return own | (fields(base) if base else set())

    return {name: fields(name) for name in parsed}


@pytest.fixture(scope="module")
def openapi_schemas() -> dict[str, dict]:
    return app.openapi()["components"]["schemas"]


def test_dashboard_types_file_exists():
    assert TYPES_FILE.is_file(), f"expected dashboard types at {TYPES_FILE}"


def test_mapping_covers_every_response_model(openapi_schemas):
    """A new response model with no dashboard type would go unnoticed."""
    read_models = {name for name in openapi_schemas if name.endswith("Out")}
    unaccounted = read_models - set(SCHEMA_TO_INTERFACE) - NOT_YET_ON_DASHBOARD

    assert not unaccounted, (
        f"{sorted(unaccounted)} has no dashboard type. Add one to types.ts and "
        "SCHEMA_TO_INTERFACE, or list it in NOT_YET_ON_DASHBOARD."
    )


@pytest.mark.parametrize(("schema_name", "interface"), SCHEMA_TO_INTERFACE.items())
def test_fields_match(schema_name, interface, openapi_schemas, dashboard_interfaces):
    assert schema_name in openapi_schemas, f"{schema_name} missing from OpenAPI"
    assert interface in dashboard_interfaces, f"{interface} missing from types.ts"

    backend_fields = set(openapi_schemas[schema_name]["properties"])
    dashboard_fields = dashboard_interfaces[interface]

    assert backend_fields == dashboard_fields, (
        f"{schema_name} and {interface} disagree: "
        f"backend-only={sorted(backend_fields - dashboard_fields)}, "
        f"dashboard-only={sorted(dashboard_fields - backend_fields)}"
    )
