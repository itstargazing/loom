"""Fuzzy matching leaves low-confidence fields blank."""

from app.services.form_match import effective_profile, match_document_fields, match_field_locally


PROFILE = {
    "full_name": "Ada Lovelace",
    "email": "ada@example.com",
    "phone": "555-0100",
    "postal_code": "02139",
    "city": "Cambridge",
}


def test_exact_and_alias_fields_fill():
    matches = match_document_fields(
        [
            {"name": "Email Address", "type": "tx"},
            {"name": "ZIP", "type": "tx"},
            {"name": "Applicant Name", "type": "tx"},
        ],
        PROFILE,
    )
    by_name = {item.field_name: item for item in matches}
    assert by_name["Email Address"].value == "ada@example.com"
    assert not by_name["Email Address"].needs_manual
    assert by_name["ZIP"].value == "02139"
    assert by_name["Applicant Name"].value == "Ada Lovelace"


def test_filename_does_not_match_name():
    match = match_field_locally("filename", "tx", PROFILE)
    assert match.value is None
    assert match.needs_manual


def test_unrelated_field_stays_blank():
    match = match_field_locally("Favorite color", "tx", PROFILE)
    assert match.value is None
    assert match.needs_manual
    assert match.confidence < 0.75


def test_synthesizes_full_name_from_parts():
    values = effective_profile({"first_name": "Ada", "last_name": "Lovelace"})
    assert values["full_name"] == "Ada Lovelace"
    match = match_field_locally("Full Name", "tx", values)
    assert match.value == "Ada Lovelace"


def test_empty_profile_values_are_skipped():
    match = match_field_locally("email", "tx", {"email": "  "})
    assert match.value is None
    assert match.needs_manual
