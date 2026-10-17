
"""Integration tests for the timetable clash workflow."""

from app.clashes import find_clashes


def test_timetable_flow_detects_overlapping_classes(sample_timetable):
    clashes = find_clashes(sample_timetable)

    assert clashes
    # Add assertions for the exact output format returned by find_clashes.
    # For example, verify that Mathematics and Physics are reported
    # as a clash if those are the expected conflicting classes.


def test_timetable_without_classes_has_no_clashes():
    # Adapt this test if an empty timetable is invalid in your app.
    clashes = find_clashes([])

    assert clashes == []
