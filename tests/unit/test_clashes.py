"""Unit tests for timetable overlap rules."""

import pytest
from app.clashes import overlaps


@pytest.mark.parametrize(
    ("start1", "end1", "start2", "end2", "expected"),
    [
        ("10:00", "11:00", "10:30", "11:30", True),
        ("10:30", "11:30", "10:00", "11:00", True),
        ("09:00", "12:00", "10:00", "11:00", True),
        ("10:00", "11:00", "09:00", "12:00", True),
        ("10:00", "11:00", "10:00", "11:00", True),
        ("10:00", "11:00", "11:00", "12:00", False),
        ("09:00", "10:00", "11:00", "12:00", False),
        ("11:00", "12:00", "09:00", "10:00", False),
        ("10:00", "10:30", "10:30", "11:00", False),
        ("09:00", "10:00", "09:30", "10:30", True),
    ],
)
def test_overlaps(start1, end1, start2, end2, expected):
    assert overlaps(start1, end1, start2, end2) is expected

from app.clashes import (
    ClashError,
    parse_hhmm,
    fmt_hhmm,
    normalise_day,
    overlaps,
    overlap_minutes,
    within_college_hours,
    validate_class,
    find_clashes,
    build_views,
    free_slots,
    workload,
)


def sample_class(**overrides):
    entry = {
        "day": "mon",
        "start": "09:00",
        "end": "10:00",
        "teacher": "Rao",
        "room": "A101",
        "batch": "CSE-3A",
        "subject": "DBMS",
    }
    entry.update(overrides)
    return entry


def test_parse_hhmm_and_format():
    assert parse_hhmm("9:00") == 540
    assert parse_hhmm("09:30") == 570
    assert fmt_hhmm(570) == "09:30"


def test_parse_hhmm_rejects_invalid_times():
    for value in ("lunch", "24:00", "10:60", "abc"):
        try:
            parse_hhmm(value)
        except ClashError:
            pass
        else:
            raise AssertionError(f"{value!r} should be rejected")


def test_normalise_day_alias_and_invalid_day():
    assert normalise_day(" Monday ") == "mon"
    try:
        normalise_day("Sunday")
    except ClashError:
        pass
    else:
        raise AssertionError("Sunday should be rejected")


def test_overlap_minutes_and_college_hours():
    assert overlap_minutes(600, 660, 630, 690) == 30
    assert overlap_minutes(600, 630, 630, 660) == 0
    assert within_college_hours(540, 600)
    assert not within_college_hours(480, 540)


def test_validate_class_normalises_entry():
    result = validate_class(sample_class(day="Monday"))
    assert result["day"] == "mon"
    assert result["start"] == 540
    assert result["end"] == 600
    assert result["teacher"] == "Rao"


def test_validate_class_rejects_invalid_duration_and_lunch():
    invalid_entries = [
        sample_class(start="10:00", end="10:00"),
        sample_class(start="10:00", end="10:15"),
        sample_class(start="09:00", end="12:30"),
        sample_class(start="08:00", end="09:00"),
        sample_class(start="12:30", end="13:30"),
    ]
    for entry in invalid_entries:
        try:
            validate_class(entry)
        except ClashError:
            pass
        else:
            raise AssertionError(f"Entry should be rejected: {entry}")


def test_validate_class_requires_all_fields():
    for field in ("teacher", "room", "batch", "subject"):
        entry = sample_class(**{field: ""})
        try:
            validate_class(entry)
        except ClashError:
            pass
        else:
            raise AssertionError(f"Missing {field} should be rejected")


def test_find_clashes_detects_room_teacher_and_batch():
    candidate = {
        "day": "mon", "start": 600, "end": 660,
        "teacher": "Rao", "room": "A101", "batch": "CSE-3A",
    }
    existing = [{
        "id": 7, "day": "mon", "start": 630, "end": 690,
        "teacher": "Rao", "room": "A101", "batch": "CSE-3A",
        "subject": "DBMS",
    }]
    results = find_clashes(candidate, existing)
    assert {item["field"] for item in results} == {"room", "teacher", "batch"}
    assert all(item["overlap_minutes"] == 30 for item in results)


def test_find_clashes_ignores_different_day_and_ignored_id():
    candidate = {
        "day": "mon", "start": 600, "end": 660,
        "teacher": "Rao", "room": "A101", "batch": "CSE-3A",
    }
    other = {
        "id": 7, "day": "tue", "start": 630, "end": 690,
        "teacher": "Rao", "room": "A101", "batch": "CSE-3A",
        "subject": "DBMS",
    }
    assert find_clashes(candidate, [other]) == []
    other["day"] = "mon"
    assert find_clashes(candidate, [other], ignore_id=7) == []


def test_build_views_groups_and_sorts_classes():
    classes = [
        {"id": 2, "day": "mon", "start": 660, "end": 720,
         "room": "A101", "teacher": "Rao", "batch": "CSE-3A",
         "subject": "OS"},
        {"id": 1, "day": "mon", "start": 600, "end": 660,
         "room": "A101", "teacher": "Rao", "batch": "CSE-3A",
         "subject": "DBMS"},
    ]
    view = build_views(classes, "room")
    assert [item["id"] for item in view["A101"]["mon"]] == [1, 2]
    assert view["A101"]["tue"] == []


def test_build_views_rejects_invalid_key():
    try:
        build_views([], "subject")
    except ClashError:
        pass
    else:
        raise AssertionError("Invalid view key should be rejected")


def test_free_slots_excludes_lunch_and_short_gaps():
    classes = [
        {"day": "mon", "start": 540, "end": 600},
        {"day": "mon", "start": 630, "end": 660},
    ]
    slots = free_slots(classes, "mon", minimum=30)
    assert {"start": "10:00", "end": "10:30", "minutes": 30} in slots
    assert not any(
        slot["start"] == "13:00" or slot["end"] == "14:00"
        for slot in slots
    )


def test_free_slots_for_other_day_and_minimum():
    slots = free_slots(
        [{"day": "tue", "start": 600, "end": 660}],
        "mon",
        minimum=180,
    )
    assert all(slot["minutes"] >= 180 for slot in slots)


def test_workload_totals_and_sorts_teachers():
    classes = [
        {"teacher": "Rao", "start": 540, "end": 600},
        {"teacher": "Rao", "start": 600, "end": 660},
        {"teacher": "Meena", "start": 540, "end": 630},
    ]
    assert workload(classes) == {"Rao": 120, "Meena": 90}
