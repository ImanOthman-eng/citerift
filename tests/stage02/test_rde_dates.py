"""Temporal evidence and chronology (SPECIFICATION.md 7.2, 7.3; directive section 14 items 8 and 9)."""

from __future__ import annotations

import pytest

from citerift.retraction.dates import TemporalEvidence, definitely_before, interval_difference_days, parse_rw_date


@pytest.mark.unit
@pytest.mark.parametrize(
    ("raw", "reported", "bounded", "flags"),
    [
        ("3/12/2015 0:00", "2015-03-12", True, ["MIDNIGHT_NOT_INSTANT"]),
        ("12/31/1999 13:45", "1999-12-31", True, ["TIME_PART_IGNORED"]),
        ("3/12/2015 12:00:00 AM", "2015-03-12", True, ["MIDNIGHT_NOT_INSTANT"]),
        ("3/12/2015 4:05:06 PM", "2015-03-12", True, ["TIME_PART_IGNORED"]),
        ("6/15/1756 0:00", "1756-06-15", True, ["MIDNIGHT_NOT_INSTANT"]),  # no modern-year cutoff
        ("2/29/2016 0:00", "2016-02-29", True, ["MIDNIGHT_NOT_INSTANT"]),
        # Day 1 may encode an unknown day, a month range, a season or a volume number: no bounds.
        ("3/1/2015 0:00", "2015-03-01", False, ["MIDNIGHT_NOT_INSTANT", "DAY_ONE_CONVENTION_POSSIBLE"]),
        ("12/1/2001 0:00", "2001-12-01", False, ["MIDNIGHT_NOT_INSTANT", "DAY_ONE_CONVENTION_POSSIBLE"]),
        ("1/1/1756 0:00", "1756-01-01", False, ["MIDNIGHT_NOT_INSTANT", "DAY_ONE_CONVENTION_POSSIBLE"]),
    ],
)
def test_rde_dates_supported_shapes(raw: str, reported: str, bounded: bool, flags: list[str]) -> None:
    te = parse_rw_date(raw, "notice_date")
    assert te.raw == raw and te.reported_calendar == reported
    assert te.bounded is bounded
    assert list(te.convention_flags) == flags
    if bounded:
        assert te.earliest == te.latest == reported and te.effective_precision == "day"
    else:
        assert te.earliest is None and te.latest is None and te.effective_precision == "unknown"
        assert te.stated_precision == "day"  # what the source states is kept apart from what it justifies


@pytest.mark.negative
@pytest.mark.parametrize(
    ("raw", "issue"),
    [
        ("", "DATE_EMPTY"),
        ("   ", "DATE_EMPTY"),
        ("2/30/2015 0:00", "DATE_CALENDAR_INVALID"),
        ("2/29/2015 0:00", "DATE_CALENDAR_INVALID"),
        ("13/2/2015 0:00", "DATE_CALENDAR_INVALID"),
        ("0/2/2015 0:00", "DATE_CALENDAR_INVALID"),
        ("2015-03-12", "DATE_UNPARSEABLE"),
        ("3/12/15 0:00", "DATE_UNPARSEABLE"),
        ("3/12/2015", "DATE_UNPARSEABLE"),
        ("Spring 2015", "DATE_UNPARSEABLE"),
        ("３/12/2015 0:00", "DATE_UNPARSEABLE"),  # non-ASCII digits are not dates
        ("3/12/2015 0:00 extra", "DATE_UNPARSEABLE"),
    ],
)
def test_rde_dates_invalid_keep_raw_with_null_bounds(raw: str, issue: str) -> None:
    te = parse_rw_date(raw, "original_publication_date")
    assert te.raw == raw and te.reported_calendar is None
    assert te.earliest is None and te.latest is None
    assert te.issues == (issue,)


@pytest.mark.negative
def test_rde_dates_invalid_time_part_is_flagged_not_dropped() -> None:
    te = parse_rw_date("3/12/2015 25:00", "notice_date")
    assert te.reported_calendar == "2015-03-12" and "DATE_TIME_PART_INVALID" in te.issues


@pytest.mark.negative
def test_rde_dates_unknown_kind_rejected() -> None:
    with pytest.raises(ValueError, match="kind"):
        parse_rw_date("3/12/2015 0:00", "retraction_event_date")


@pytest.mark.unit
def test_rde_dates_kinds_are_kept_apart() -> None:
    a = parse_rw_date("3/12/2015 0:00", "notice_date")
    b = parse_rw_date("3/12/2015 0:00", "original_publication_date")
    assert a.kind != b.kind and a.reported_calendar == b.reported_calendar
    assert a != b


@pytest.mark.unit
def test_rde_chronology_is_a_partial_order() -> None:
    early = parse_rw_date("3/12/2015 0:00", "notice_date")
    late = parse_rw_date("4/20/2016 0:00", "notice_date")
    same = parse_rw_date("3/12/2015 9:00", "notice_date")
    day_one = parse_rw_date("6/1/2017 0:00", "notice_date")
    bad = parse_rw_date("2/30/2018 0:00", "notice_date")
    assert definitely_before(early, late) and not definitely_before(late, early)
    assert not definitely_before(early, same) and not definitely_before(same, early)  # ties stay unresolved
    for unknown in (day_one, bad, None):
        assert not definitely_before(early, unknown) and not definitely_before(unknown, early)
    assert interval_difference_days(late, early) == (405, 405)
    assert interval_difference_days(day_one, early) is None  # never invented bounds


@pytest.mark.unit
def test_rde_require_bounds_view_withholds_only_unjustified_values() -> None:
    day_one = parse_rw_date("6/1/2017 0:00", "notice_date")
    withheld = day_one.without_unjustified_value()
    assert withheld.reported_calendar is None and "WITHHELD_UNJUSTIFIED_PRECISION" in withheld.issues
    assert withheld.raw == day_one.raw  # the source value itself is kept
    exact = parse_rw_date("6/2/2017 0:00", "notice_date")
    assert exact.without_unjustified_value() == exact
    empty = parse_rw_date("", "notice_date")
    assert empty.without_unjustified_value() == empty


@pytest.mark.unit
def test_rde_dates_round_trip_json() -> None:
    for raw in ("3/12/2015 0:00", "6/1/2017 0:00", "", "x"):
        te = parse_rw_date(raw, "notice_date")
        assert TemporalEvidence.from_json(te.to_json()) == te
