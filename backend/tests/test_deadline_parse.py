from datetime import UTC, datetime

from app.services.deadline_parse import date_identity, parse_due


def test_iso_dates_resolve():
    resolved = parse_due("2026-09-15")
    assert resolved == datetime(2026, 9, 15, tzinfo=UTC)


def test_month_name_with_year():
    resolved = parse_due("October 20, 2026")
    assert resolved == datetime(2026, 10, 20, tzinfo=UTC)


def test_month_name_without_year_rolls_forward_if_already_past():
    # Seen in August, so March without a year is next March.
    resolved = parse_due("March 3", occurred_at="2026-08-28T10:00:00+00:00")
    assert resolved == datetime(2027, 3, 3, tzinfo=UTC)


def test_next_friday_from_a_wednesday():
    # 2026-08-28 is a Friday; "next Friday" is a week later.
    resolved = parse_due("next Friday", occurred_at="2026-08-28T10:00:00+00:00")
    assert resolved == datetime(2026, 9, 4, tzinfo=UTC)


def test_unparseable_dates_stay_unresolved():
    assert parse_due("end of term") is None


def test_date_identity_prefers_the_resolved_day():
    assert date_identity("September 15, 2026") == "2026-09-15"
    assert date_identity("end of term") == "end of term"
