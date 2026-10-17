
"""Unit tests for timetable clash detection."""

import pytest

from app.clashes import (
    overlap_minutes,
    normalise_day,
    fmt_hhmm,
)


def test_overlap_minutes_for_overlapping_intervals():
    # Example: 10:00–11:00 and 10:30–11:30
    assert overlap_minutes("10:00", "11:00", "10:30", "11:30") == 30


def test_overlap_minutes_for_non_overlapping_intervals():
    assert overlap_minutes("09:00", "10:00", "10:00", "11:00") == 0


def test_overlap_minutes_for_identical_intervals():
    assert overlap_minutes("10:00", "11:00", "10:00", "11:00") == 60


@pytest.mark.parametrize(
    ("day", "expected"),
    [
        ("Monday", "Monday"),
        ("monday", "Monday"),
        (" MONDAY ", "Monday"),
    ],
)
def test_normalise_day(day, expected):
    assert normalise_day(day) == expected


def test_fmt_hhmm():
    # Change the input to match your function's expected format.
    assert fmt_hhmm(9, 30) == "09:30"
