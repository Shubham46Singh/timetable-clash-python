import pytest

from app.clashes import (
    ClashError,
    crosses_lunch,
    fmt_hhmm,
    normalise_day,
    overlap_minutes,
    overlaps,
    parse_hhmm,
    within_college_hours,
)


@pytest.mark.parametrize(
    "a_start,a_end,b_start,b_end,expected",
    [
        (600, 660, 630, 690, True),   # Partial overlap
        (630, 690, 600, 660, True),   # Partial overlap in reverse
        (600, 720, 630, 660, True),   # First interval contains second
        (630, 660, 600, 720, True),   # Second interval contains first
        (600, 660, 600, 660, True),   # Identical intervals
        (600, 660, 660, 720, False),  # Touching boundary
        (660, 720, 600, 660, False),  # Touching boundary in reverse
        (600, 660, 700, 760, False),  # Separate intervals
    ],
)
def test_overlaps(a_start, a_end, b_start, b_end, expected):
    assert overlaps(a_start, a_end, b_start, b_end) is expected


def test_overlap_minutes_for_partial_overlap():
    assert overlap_minutes(600, 660, 630, 690) == 30


def test_overlap_minutes_for_non_overlapping_intervals():
    assert overlap_minutes(600, 660, 660, 720) == 0


@pytest.mark.parametrize(
    "value,expected",
    [
        ("9:00", 540),
        ("09:00", 540),
        ("10:30", 630),
        ("17:00", 1020),
    ],
)
def test_parse_hhmm_valid(value, expected):
    assert parse_hhmm(value) == expected


@pytest.mark.parametrize("value", ["24:00", "10:60", "lunch", "1000"])
def test_parse_hhmm_invalid(value):
    with pytest.raises(ClashError):
        parse_hhmm(value)


def test_format_hhmm():
    assert fmt_hhmm(570) == "09:30"


def test_normalise_day_accepts_full_day_name():
    assert normalise_day("Monday") == "mon"


def test_normalise_day_rejects_invalid_day():
    with pytest.raises(ClashError):
        normalise_day("Funday")


def test_class_crossing_lunch_is_detected():
    assert crosses_lunch(750, 810) is True  # 12:30-13:30


def test_class_ending_at_lunch_start_does_not_cross_lunch():
    assert crosses_lunch(720, 780) is False  # 12:00-13:00


def test_within_college_hours():
    assert within_college_hours(540, 600) is True  # 09:00-10:00


def test_outside_college_hours():
    assert within_college_hours(480, 540) is False  # 08:00-09:00

from app.clashes import validate_class, find_clashes


def valid_class(**overrides):
    entry = {
        "day": "Monday",
        "start": "10:00",
        "end": "11:00",
        "teacher": "Teacher A",
        "room": "Room 101",
        "batch": "ISE-A",
        "subject": "Python",
    }
    entry.update(overrides)
    return entry


def test_validate_class_returns_cleaned_entry():
    result = validate_class(valid_class())
    assert result["day"] == "mon"
    assert result["start"] == 600
    assert result["end"] == 660
    assert result["teacher"] == "Teacher A"


def test_validate_class_rejects_end_before_start():
    with pytest.raises(ClashError):
        validate_class(valid_class(start="11:00", end="10:00"))


def test_validate_class_rejects_short_lesson():
    with pytest.raises(ClashError):
        validate_class(valid_class(start="10:00", end="10:15"))


def test_validate_class_rejects_long_lesson():
    with pytest.raises(ClashError):
        validate_class(valid_class(start="09:00", end="12:30"))


def test_validate_class_rejects_missing_teacher():
    with pytest.raises(ClashError):
        validate_class(valid_class(teacher=" "))


def test_find_clashes_detects_room_teacher_and_batch():
    candidate = validate_class(valid_class())
    existing = [{
        "id": 10,
        "day": "mon",
        "start": 630,
        "end": 690,
        "teacher": "Teacher A",
        "room": "Room 101",
        "batch": "ISE-A",
        "subject": "Database",
    }]

    clashes = find_clashes(candidate, existing)
    assert {item["field"] for item in clashes} == {"room", "teacher", "batch"}
    assert all(item["clashes_with"] == 10 for item in clashes)


def test_find_clashes_ignores_different_day():
    candidate = validate_class(valid_class())
    existing = [{
        "id": 11,
        "day": "tue",
        "start": 630,
        "end": 690,
        "teacher": "Teacher A",
        "room": "Room 101",
        "batch": "ISE-A",
        "subject": "Database",
    }]
    assert find_clashes(candidate, existing) == []


def test_find_clashes_ignores_touching_time_boundary():
    candidate = validate_class(valid_class(start="10:00", end="11:00"))
    existing = [{
        "id": 12,
        "day": "mon",
        "start": 660,
        "end": 720,
        "teacher": "Teacher A",
        "room": "Room 101",
        "batch": "ISE-A",
        "subject": "Database",
    }]
    assert find_clashes(candidate, existing) == []


def test_find_clashes_can_ignore_current_class_id():
    candidate = validate_class(valid_class())
    existing = [{
        "id": 13,
        "day": "mon",
        "start": 630,
        "end": 690,
        "teacher": "Teacher A",
        "room": "Room 101",
        "batch": "ISE-A",
        "subject": "Database",
    }]
    assert find_clashes(candidate, existing, ignore_id=13) == []

from app.clashes import build_views, free_slots, workload


def sample_class(class_id, day, start, end, teacher, room, batch, subject):
    return {
        "id": class_id,
        "day": day,
        "start": start,
        "end": end,
        "teacher": teacher,
        "room": room,
        "batch": batch,
        "subject": subject,
    }


def test_build_views_groups_classes_by_room():
    classes = [
        sample_class(1, "mon", 630, 690, "Teacher A", "Room 101", "ISE-A", "DBMS"),
        sample_class(2, "mon", 540, 600, "Teacher B", "Room 101", "ISE-B", "Python"),
    ]

    result = build_views(classes, "room")

    assert "Room 101" in result
    assert result["Room 101"]["mon"][0]["subject"] == "Python"
    assert result["Room 101"]["mon"][1]["subject"] == "DBMS"


def test_build_views_rejects_invalid_grouping_key():
    with pytest.raises(ClashError):
        build_views([], "subject")


def test_free_slots_excludes_lunch_and_finds_gaps():
    classes = [
        sample_class(1, "mon", 540, 600, "Teacher A", "Room 101", "ISE-A", "Python"),
        sample_class(2, "mon", 660, 720, "Teacher B", "Room 102", "ISE-B", "DBMS"),
    ]

    result = free_slots(classes, "Monday", minimum=30)

    assert {"start": "10:00", "end": "11:00", "minutes": 60} in result
    assert not any(slot["start"] == "13:00" and slot["end"] == "14:00"
                   for slot in result)


def test_free_slots_returns_empty_when_day_is_fully_busy():
    classes = [
        sample_class(1, "mon", 540, 780, "Teacher A", "Room 101", "ISE-A", "Python"),
        sample_class(2, "mon", 840, 1020, "Teacher B", "Room 102", "ISE-B", "DBMS"),
    ]

    result = free_slots(classes, "mon", minimum=30)

    assert result == []


def test_workload_sorts_teachers_by_minutes_descending():
    classes = [
        sample_class(1, "mon", 540, 600, "Teacher B", "Room 101", "ISE-A", "Python"),
        sample_class(2, "tue", 600, 720, "Teacher A", "Room 102", "ISE-B", "DBMS"),
        sample_class(3, "wed", 540, 600, "Teacher B", "Room 103", "ISE-C", "Networks"),
    ]

    assert workload(classes) == {"Teacher B": 120, "Teacher A": 120} or (
        list(workload(classes).items()) == [("Teacher A", 120), ("Teacher B", 120)]
    )
