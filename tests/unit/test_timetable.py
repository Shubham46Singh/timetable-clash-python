"""Unit tests for timetable lunch rules."""

from app.clashes import crosses_lunch


def test_class_before_lunch_does_not_cross():
    assert crosses_lunch(540, 600) is False


def test_class_after_lunch_does_not_cross():
    assert crosses_lunch(840, 900) is False


def test_class_overlapping_lunch():
    assert crosses_lunch(750, 810) is True


def test_class_inside_lunch():
    assert crosses_lunch(790, 820) is True


def test_class_overlapping_lunch_from_before():
    assert crosses_lunch(750, 800) is True


def test_class_overlapping_lunch_until_after():
    assert crosses_lunch(830, 870) is True


def test_class_ends_at_lunch_start():
    assert crosses_lunch(720, 780) is False


def test_class_starts_at_lunch_end():
    assert crosses_lunch(840, 900) is False
