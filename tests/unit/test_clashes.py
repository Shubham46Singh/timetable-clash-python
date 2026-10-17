
"""Unit tests for timetable and clash-detection logic."""

import pytest

from app.clashes import (
    ClashError,
    build_views,
    crosses_lunch,
    find_clashes,
    fmt_hhmm,
    free_slots,
    normalise_day,
    overlap_minutes,
    overlaps,
    parse_hhmm,
    validate_class,
    within_college_hours,
    workload,
)


def minutes(value):
    return parse_hhmm(value)


def make_class(**overrides):
    item = {
        "id": 1,
        "day": "mon",
        "start": minutes("10:00"),
        "end": minutes("11:00"),
        "subject": "DBMS",
        "teacher": "Rao",
        "room": "A101",
        "batch": "CSE-3A",
    }
    item.update(overrides)
    return item


def make_entry(**overrides):
    item = {
        "day": "mon",
        "start": "10:00",
        "end": "11:00",
        "subject": "DBMS",
        "teacher": "Rao",
        "room": "A101",
        "batch": "CSE-3A",
    }
    item.update(overrides)
    return item


def test_parse_and_format_time():
    assert parse_hhmm("09:30") == 570
    assert parse_hhmm("9:30") == 570
    assert fmt_hhmm(570) == "09:30"
    assert fmt_hhmm(0) == "00:00"


@pytest.mark.parametrize(
    "value",
    ["24:00", "10:60", "lunch", "", "1000", "ab:cd"],
)
def test_invalid_time_is_rejected(value):
    with pytest.raises(ClashError):
        parse_hhmm(value)


def test_normalise_day():
    assert normalise_day("Monday") == "mon"
    assert normalise_day(" TUE ") == "tue"


def test_invalid_day_is_rejected():
    with pytest.raises(ClashError):
        normalise_day("Sunday")


@pytest.mark.parametrize(
    "a_start,a_end,b_start,b_end,expected",
    [
        ("09:30", "10:30", "10:00", "11:00", True),
        ("10:00", "11:00", "10:30", "11:30", True),
        ("09:00", "12:00", "10:00", "11:00", True),
        ("10:00", "11:00", "11:00", "12:00", False),
        ("09:00", "10:00", "14:00", "15:00", False),
    ],
)
def test_overlaps(a_start, a_end, b_start, b_end, expected):
    assert overlaps(
        minutes(a_start),
        minutes(a_end),
        minutes(b_start),
        minutes(b_end),
    ) is expected


def test_overlap_minutes():
    assert overlap_minutes(600, 660, 630, 690) == 30
    assert overlap_minutes(600, 660, 660, 720) == 0


def test_lunch_and_college_hours():
    assert crosses_lunch(minutes("12:30"), minutes("13:30"))
    assert not crosses_lunch(minutes("12:00"), minutes("13:00"))
    assert within_college_hours(minutes("09:00"), minutes("17:00"))
    assert not within_college_hours(minutes("08:00"), minutes("09:00"))


def test_valid_class_is_normalised():
    result = validate_class(make_entry(day="Monday", subject=" DBMS "))

    assert result["day"] == "mon"
    assert result["start"] == 600
    assert result["end"] == 660
    assert result["subject"] == "DBMS"


@pytest.mark.parametrize(
    "changes",
    [
        {"start": "11:00", "end": "10:00"},
        {"start": "10:00", "end": "10:00"},
        {"start": "10:00", "end": "10:20"},
        {"start": "08:00", "end": "09:00"},
        {"start": "12:30", "end": "13:30"},
        {"day": "Sunday"},
        {"start": "lunch"},
        {"teacher": " "},
        {"room": " "},
        {"batch": " "},
        {"subject": " "},
    ],
)
def test_invalid_class_is_rejected(changes):
    with pytest.raises(ClashError):
        validate_class(make_entry(**changes))


def test_room_clash_is_detected():
    candidate = make_class()
    existing = [make_class(id=2, teacher="Iyer", batch="CSE-3B")]

    clashes = find_clashes(candidate, existing)

    assert [item["field"] for item in clashes] == ["room"]


def test_teacher_clash_is_detected():
    candidate = make_class()
    existing = [make_class(id=2, room="B201", batch="CSE-3B")]

    clashes = find_clashes(candidate, existing)

    assert [item["field"] for item in clashes] == ["teacher"]


def test_batch_clash_is_detected():
    candidate = make_class()
    existing = [make_class(id=2, room="B201", teacher="Iyer")]

    clashes = find_clashes(candidate, existing)

    assert [item["field"] for item in clashes] == ["batch"]


def test_different_day_does_not_clash():
    assert find_clashes(
        make_class(),
        [make_class(id=2, day="tue")],
    ) == []


def test_back_to_back_classes_do_not_clash():
    assert find_clashes(
        make_class(),
        [make_class(id=2, start=660, end=720)],
    ) == []


def test_build_views_groups_classes_by_batch():
    classes = [
        make_class(id=1, batch="CSE-3A"),
        make_class(id=2, batch="CSE-3B"),
    ]

    result = build_views(classes, "batch")

    assert "CSE-3A" in result
    assert "CSE-3B" in result
    assert len(result["CSE-3A"]["mon"]) == 1


def test_build_views_rejects_invalid_key():
    with pytest.raises(ClashError):
        build_views([make_class()], "subject")


def test_free_slots_excludes_lunch():
    result = free_slots([], "mon")

    assert [(slot["start"], slot["end"]) for slot in result] == [
        ("09:00", "13:00"),
        ("14:00", "17:00"),
    ]


def test_free_slots_filters_short_gaps():
    result = free_slots([], "mon", minimum=240)

    assert all(slot["minutes"] >= 240 for slot in result)


def test_workload_totals():
    classes = [
        make_class(teacher="Rao", start=540, end=600),
        make_class(id=2, teacher="Rao", start=600, end=660),
        make_class(id=3, teacher="Iyer", start=540, end=660),
    ]

    assert workload(classes) == {"Iyer": 120, "Rao": 120}
