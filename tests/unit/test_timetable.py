
"""Unit tests for timetable rules."""

import pytest

from app.clashes import crosses_lunch


def test_crosses_lunch_when_class_spans_lunch():
    # Assumes the function accepts start and end times.
    assert crosses_lunch("12:30", "13:30") is True


def test_crosses_lunch_when_class_is_before_lunch():
    assert crosses_lunch("09:00", "10:00") is False


def test_crosses_lunch_when_class_is_after_lunch():
    assert crosses_lunch("14:00", "15:00") is False


def test_crosses_lunch_for_class_ending_at_lunch_start():
    assert crosses_lunch("11:00", "12:00") is False
