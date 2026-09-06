from app.services.deadline_extract import document_identity, extract_deadlines


SYLLABUS = """
CS101 Syllabus
Problem Set 3 is due 2026-09-15 and must be submitted through the course portal.
Midterm exam is on October 20, 2026.
RSVP for the review session by 2026-10-18.
The campus was founded in 1861 and that year is not an obligation.
"""


def test_syllabus_yields_every_obligation_not_just_the_first():
    found = extract_deadlines(
        SYLLABUS,
        page_title="CS101 Syllabus",
        source_url="https://university.edu/cs101/syllabus",
        occurred_at="2026-08-28T10:00:00+00:00",
    )
    titles = {item.title for item in found}
    dates = {item.due_text for item in found}

    assert len(found) >= 3
    assert any("Problem Set 3" in title for title in titles)
    assert "2026-09-15" in dates
    assert "October 20, 2026" in dates
    assert "2026-10-18" in dates
    assert not any("1861" in item.due_text for item in found)


def test_kinds_are_labelled_from_nearby_wording():
    found = extract_deadlines(
        SYLLABUS,
        page_title="CS101 Syllabus",
        source_url="https://university.edu/cs101/syllabus",
    )
    by_date = {item.due_text: item for item in found}
    assert by_date["2026-09-15"].kind == "assignment_due"
    assert by_date["October 20, 2026"].kind == "exam"
    assert by_date["2026-10-18"].kind == "rsvp"


def test_a_shopping_page_is_not_a_calendar():
    found = extract_deadlines(
        "Price $385.00. In stock, free shipping. Released January 2020.",
        page_title="HHKB Professional",
        source_url="https://shop.example.com/keyboards/hhkb",
    )
    assert found == []


def test_document_identity_drops_filename_versions():
    a = document_identity("https://university.edu/cs101/syllabus.pdf")
    b = document_identity("https://university.edu/cs101/syllabus-v2.pdf")
    c = document_identity("https://university.edu/cs202/syllabus.pdf")
    assert a == b
    assert a != c
