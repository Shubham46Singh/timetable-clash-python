"""Unit tests for app/clashes.py - pure logic, no database, no network."""
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


def m(text):
    return parse_hhmm(text)


# ---------------------------------------------------------------- overlaps

class TestOverlaps:
    def test_partial_overlap_from_the_left(self):
        assert overlaps(m("09:30"), m("10:30"), m("10:00"), m("11:00"))

    def test_partial_overlap_from_the_right(self):
        # THE case students miss: 10:00-11:00 vs 10:30-11:30
        assert overlaps(m("10:00"), m("11:00"), m("10:30"), m("11:30"))

    def test_a_contains_b(self):
        assert overlaps(m("09:00"), m("12:00"), m("10:00"), m("11:00"))

    def test_b_contains_a(self):
        assert overlaps(m("10:00"), m("11:00"), m("09:00"), m("12:00"))

    def test_identical_slots(self):
        assert overlaps(m("10:00"), m("11:00"), m("10:00"), m("11:00"))

    def test_touching_end_to_start_is_not_a_clash(self):
        assert not overlaps(m("10:00"), m("11:00"), m("11:00"), m("12:00"))

    def test_touching_start_to_end_is_not_a_clash(self):
        assert not overlaps(m("11:00"), m("12:00"), m("10:00"), m("11:00"))

    def test_completely_separate(self):
        assert not overlaps(m("09:00"), m("10:00"), m("14:00"), m("15:00"))

    def test_completely_separate_reversed(self):
        assert not overlaps(m("14:00"), m("15:00"), m("09:00"), m("10:00"))

    def test_one_minute_overlap_is_a_clash(self):
        assert overlaps(m("10:00"), m("11:00"), m("10:59"), m("12:00"))

    def test_overlap_is_symmetric(self):
        assert overlaps(m("10:00"), m("11:00"), m("10:30"), m("11:30")) == \
            overlaps(m("10:30"), m("11:30"), m("10:00"), m("11:00"))


class TestOverlapMinutes:
    def test_partial(self):
        assert overlap_minutes(m("10:00"), m("11:00"), m("10:30"), m("11:30")) == 30

    def test_containment(self):
        assert overlap_minutes(m("09:00"), m("12:00"), m("10:00"), m("11:00")) == 60

    def test_touching_is_zero(self):
        assert overlap_minutes(m("10:00"), m("11:00"), m("11:00"), m("12:00")) == 0

    def test_separate_is_zero_not_negative(self):
        assert overlap_minutes(m("09:00"), m("10:00"), m("15:00"), m("16:00")) == 0


# ------------------------------------------------------------ find_clashes

def cls(**kw):
    base = {"id": 1, "day": "mon", "start": m("10:00"), "end": m("11:00"),
            "subject": "DBMS", "teacher": "Rao", "room": "A101", "batch": "CSE-3A"}
    base.update(kw)
    return base


class TestFindClashes:
    def test_no_existing_classes(self):
        assert find_clashes(cls(), []) == []

    def test_room_clash_only(self):
        existing = [cls(id=2, teacher="Iyer", batch="CSE-3B")]
        out = find_clashes(cls(), existing)
        assert [c["field"] for c in out] == ["room"]

    def test_teacher_clash_only(self):
        existing = [cls(id=2, room="B201", batch="CSE-3B")]
        out = find_clashes(cls(), existing)
        assert [c["field"] for c in out] == ["teacher"]

    def test_batch_clash_only(self):
        existing = [cls(id=2, room="B201", teacher="Iyer")]
        out = find_clashes(cls(), existing)
        assert [c["field"] for c in out] == ["batch"]

    def test_all_three_at_once(self):
        out = find_clashes(cls(), [cls(id=2)])
        assert sorted(c["field"] for c in out) == ["batch", "room", "teacher"]

    def test_same_slot_different_day_clashes_with_nothing(self):
        assert find_clashes(cls(), [cls(id=2, day="tue")]) == []

    def test_adjacent_slot_same_resources_does_not_clash(self):
        existing = [cls(id=2, start=m("11:00"), end=m("12:00"))]
        assert find_clashes(cls(), existing) == []

    def test_partial_overlap_is_reported_with_minutes(self):
        existing = [cls(id=2, start=m("10:30"), end=m("11:30"))]
        out = find_clashes(cls(), existing)
        assert out and all(c["overlap_minutes"] == 30 for c in out)

    def test_clash_explains_what_it_collided_with(self):
        out = find_clashes(cls(), [cls(id=7, subject="OS")])
        room = next(c for c in out if c["field"] == "room")
        assert room["clashes_with"] == 7
        assert room["subject"] == "OS"
        assert room["window"] == "10:00-11:00"
        assert room["day"] == "mon"
        assert room["value"] == "A101"

    def test_comparison_is_case_insensitive(self):
        out = find_clashes(cls(room="a101"), [cls(id=2, teacher="X", batch="Y")])
        assert [c["field"] for c in out] == ["room"]

    def test_ignore_id_skips_the_class_itself(self):
        assert find_clashes(cls(), [cls(id=1)], ignore_id=1) == []

    def test_multiple_existing_classes_each_reported(self):
        existing = [cls(id=2, teacher="Iyer", batch="B"), cls(id=3, room="Z", batch="B")]
        out = find_clashes(cls(), existing)
        assert sorted(c["field"] for c in out) == ["room", "teacher"]


# ------------------------------------------------------------- parse / fmt

class TestParseHHMM:
    @pytest.mark.parametrize("text,expected", [
        ("9:00", 540), ("09:00", 540), ("00:00", 0), ("23:59", 1439),
        (" 10:15 ", 615), ("12:30", 750),
    ])
    def test_valid(self, text, expected):
        assert parse_hhmm(text) == expected

    @pytest.mark.parametrize("text", ["24:00", "10:60", "lunch", "", "1000", "ab:cd", "-1:30", "10:"])
    def test_invalid(self, text):
        with pytest.raises(ClashError):
            parse_hhmm(text)


def test_fmt_hhmm_pads():
    assert fmt_hhmm(540) == "09:00"
    assert fmt_hhmm(0) == "00:00"
    assert fmt_hhmm(1005) == "16:45"


class TestNormaliseDay:
    def test_short(self):
        assert normalise_day("mon") == "mon"

    def test_full_name_any_case(self):
        assert normalise_day(" Monday ") == "mon"

    @pytest.mark.parametrize("bad", ["sun", "funday", "", None])
    def test_bad(self, bad):
        with pytest.raises(ClashError):
            normalise_day(bad)


# ----------------------------------------------------------------- lunch etc

class TestLunchAndHours:
    def test_straddling_lunch_is_refused(self):
        assert crosses_lunch(m("12:30"), m("13:30"))

    def test_ending_exactly_at_lunch_is_fine(self):
        assert not crosses_lunch(m("12:00"), m("13:00"))

    def test_starting_exactly_when_lunch_ends_is_fine(self):
        assert not crosses_lunch(m("14:00"), m("15:00"))

    def test_inside_lunch(self):
        assert crosses_lunch(m("13:15"), m("13:45"))

    def test_within_hours(self):
        assert within_college_hours(m("09:00"), m("17:00"))
        assert not within_college_hours(m("08:59"), m("10:00"))
        assert not within_college_hours(m("16:00"), m("17:01"))


# ------------------------------------------------------------ validate_class

def entry(**kw):
    base = {"day": "mon", "start": "10:00", "end": "11:00", "subject": "DBMS",
            "teacher": "Rao", "room": "A101", "batch": "CSE-3A"}
    base.update(kw)
    return base


class TestValidateClass:
    def test_valid_entry_is_cleaned_into_minutes(self):
        out = validate_class(entry(day="Monday", subject="  DBMS "))
        assert out["day"] == "mon"
        assert out["start"] == 600 and out["end"] == 660
        assert out["subject"] == "DBMS"

    def test_accepts_minutes_as_ints(self):
        out = validate_class(entry(start=600, end=660))
        assert (out["start"], out["end"]) == (600, 660)

    def test_end_before_start(self):
        with pytest.raises(ClashError, match="end after"):
            validate_class(entry(start="11:00", end="10:00"))

    def test_zero_length(self):
        with pytest.raises(ClashError, match="end after"):
            validate_class(entry(start="10:00", end="10:00"))

    def test_too_short(self):
        with pytest.raises(ClashError, match="shorter"):
            validate_class(entry(start="10:00", end="10:20"))

    def test_too_long(self):
        with pytest.raises(ClashError, match="longer"):
            validate_class(entry(start="09:00", end="12:30"))

    def test_longest_allowed_lesson(self):
        assert validate_class(entry(start="09:00", end="12:00"))["end"] == 720

    def test_before_college_hours(self):
        with pytest.raises(ClashError, match="outside college hours"):
            validate_class(entry(start="08:00", end="09:00"))

    def test_after_college_hours(self):
        with pytest.raises(ClashError, match="outside college hours"):
            validate_class(entry(start="16:30", end="17:30"))

    def test_runs_into_lunch(self):
        with pytest.raises(ClashError, match="lunch"):
            validate_class(entry(start="12:30", end="13:30"))

    def test_ends_exactly_at_lunch_is_accepted(self):
        assert validate_class(entry(start="12:00", end="13:00"))["end"] == 780

    def test_bad_day(self):
        with pytest.raises(ClashError):
            validate_class(entry(day="sunday"))

    def test_bad_time_text(self):
        with pytest.raises(ClashError):
            validate_class(entry(start="lunch"))

    @pytest.mark.parametrize("field", ["teacher", "room", "batch", "subject"])
    def test_missing_field(self, field):
        with pytest.raises(ClashError, match=field):
            validate_class(entry(**{field: "  "}))


# ---------------------------------------------------- build_views / free_slots

def row(**kw):
    base = {"id": 1, "day": "mon", "start": 540, "end": 600, "subject": "S",
            "teacher": "T", "room": "R", "batch": "B"}
    base.update(kw)
    return base


class TestBuildViews:
    def test_groups_by_key(self):
        classes = [row(id=1, batch="A"), row(id=2, batch="B"), row(id=3, batch="A", day="tue")]
        view = build_views(classes, "batch")
        assert set(view) == {"A", "B"}
        assert len(view["A"]["mon"]) == 1 and len(view["A"]["tue"]) == 1

    def test_each_day_sorted_by_start_and_formatted(self):
        classes = [row(id=1, start=660, end=720), row(id=2, start=540, end=600)]
        day = build_views(classes, "teacher")["T"]["mon"]
        assert [c["start"] for c in day] == ["09:00", "11:00"]
        assert day[0]["end"] == "10:00"

    def test_every_day_present_even_when_empty(self):
        view = build_views([row()], "room")
        assert list(view["R"]) == ["mon", "tue", "wed", "thu", "fri", "sat"]
        assert view["R"]["fri"] == []

    def test_invalid_key(self):
        with pytest.raises(ClashError):
            build_views([row()], "subject")

    def test_empty(self):
        assert build_views([], "room") == {}


class TestFreeSlots:
    def test_empty_day_is_split_by_lunch(self):
        gaps = free_slots([], "mon")
        assert [(g["start"], g["end"]) for g in gaps] == [("09:00", "13:00"), ("14:00", "17:00")]

    def test_class_splits_a_gap(self):
        gaps = free_slots([row(start=600, end=660)], "mon")
        assert [(g["start"], g["end"]) for g in gaps] == [
            ("09:00", "10:00"), ("11:00", "13:00"), ("14:00", "17:00")]

    def test_minimum_filters_short_gaps(self):
        gaps = free_slots([row(start=600, end=660)], "mon", minimum=90)
        assert [(g["start"], g["end"]) for g in gaps] == [("11:00", "13:00"), ("14:00", "17:00")]

    def test_other_days_are_ignored(self):
        assert free_slots([row(day="tue")], "mon") == free_slots([], "mon")

    def test_class_touching_lunch_merges(self):
        gaps = free_slots([row(start=720, end=780)], "mon")
        assert [(g["start"], g["end"]) for g in gaps] == [("09:00", "12:00"), ("14:00", "17:00")]

    def test_minutes_reported(self):
        assert free_slots([], "mon")[0]["minutes"] == 240

    def test_fully_booked_day(self):
        full = [row(start=540, end=780), row(start=840, end=1020)]
        assert free_slots(full, "mon") == []

    def test_bad_day(self):
        with pytest.raises(ClashError):
            free_slots([], "sun")


def test_workload_sums_and_sorts():
    classes = [row(teacher="B", start=540, end=600), row(teacher="A", start=540, end=660),
               row(teacher="B", start=600, end=660)]
    assert workload(classes) == {"A": 120, "B": 120}
    assert list(workload(classes)) == ["A", "B"]  # tie broken by name
    assert workload([]) == {}
