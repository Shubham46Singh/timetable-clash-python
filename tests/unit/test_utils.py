
"""Unit tests for timetable helper functions."""

import pytest

from app.clashes import normalise_day


@pytest.mark.parametrize(
    "day",
    [
        "Monday",
        "Tuesday",
        "Wednesday",
        "Thursday",
        "Friday",
        "Saturday",
        "Sunday",
    ],
)
def test_normalise_day_accepts_weekday_names(day):
    result = normalise_day(day)

    assert isinstance(result, str)
    assert result != ""


def test_normalise_day_handles_whitespace():
    assert normalise_day(" Monday ") == normalise_day("Monday")
