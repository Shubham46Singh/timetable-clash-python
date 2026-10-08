"""Pure timetable and clash rules. No database, no HTTP.

The whole module works in minutes past midnight, because comparing "10:30"
to "11:00" as strings works right up until somebody writes "9:00".

What is worth testing
---------------------
* ``overlaps`` - the case everybody gets wrong: 10:00-11:00 and 10:30-11:30
  DO clash, even though neither the start nor the end matches. Also test
  full containment, identical slots, and the boundary pair 10:00-11:00 and
  11:00-12:00, which must NOT clash because the intervals are half-open.
* ``find_clashes`` - same room, same teacher, same batch, each on its own,
  and a class on a different day that must not clash with any of them.
* ``crosses_lunch`` - a class 12:30-13:30 straddles the break and is refused;
  one that ends exactly at 13:00 is fine.
* ``validate_class`` - end before start, zero length, outside college hours,
  a slot shorter or longer than the allowed lesson length, a bad day name.
* ``parse_hhmm`` - "9:00", "09:00", "24:00", "10:60", "lunch".
* ``build_views`` and ``free_slots`` - grouping and the gaps between classes.
"""

DAYS = ("mon", "tue", "wed", "thu", "fri", "sat")
_DAY_ALIASES = {
    "monday": "mon", "tuesday": "tue", "wednesday": "wed",
    "thursday": "thu", "friday": "fri", "saturday": "sat",
}

# College hours and the protected lunch break, in minutes past midnight.
DAY_START = 9 * 60        # 09:00
DAY_END = 17 * 60         # 17:00
LUNCH_START = 13 * 60     # 13:00
LUNCH_END = 14 * 60       # 14:00

MIN_LESSON = 30
MAX_LESSON = 180


class ClashError(ValueError):
    """A timetable entry that must be refused, with a readable reason."""


def parse_hhmm(text):
    """"09:30" -> 570. Accepts "9:30" too; refuses anything else."""
    s = str(text).strip()
    if ":" not in s:
        raise ClashError("%r is not a time, expected HH:MM" % (text,))
    h, _, m = s.partition(":")
    try:
        h, m = int(h), int(m)
    except ValueError:
        raise ClashError("%r is not a time, expected HH:MM" % (text,))
    if not (0 <= h <= 23) or not (0 <= m <= 59):
        raise ClashError("%r is not a real time of day" % (text,))
    return h * 60 + m


def fmt_hhmm(minutes):
    """570 -> "09:30"."""
    minutes = int(minutes)
    return "%02d:%02d" % (minutes // 60, minutes % 60)


def normalise_day(day):
    d = str(day or "").strip().lower()
    d = _DAY_ALIASES.get(d, d)
    if d not in DAYS:
        raise ClashError("%r is not a teaching day (expected one of %s)"
                         % (day, ", ".join(DAYS)))
    return d


def overlaps(a_start, a_end, b_start, b_end):
    """Do two intervals on the same day collide?

    Overlap is not equality. The test is whether each starts before the
    other ends, which catches partial overlap, full containment and exact
    duplication in one line.

    The intervals are half-open - [start, end) - so a class ending at 11:00
    and one starting at 11:00 are back to back, not a clash. Students walk
    out as the next lot walk in.
    """
    return a_start < b_end and b_start < a_end


def overlap_minutes(a_start, a_end, b_start, b_end):
    """How many minutes two intervals share. 0 when they do not clash."""
    return max(0, min(a_end, b_end) - max(a_start, b_start))


def crosses_lunch(start, end):
    """Does this slot eat into the protected lunch break?"""
    return overlaps(start, end, LUNCH_START, LUNCH_END)


def within_college_hours(start, end):
    return DAY_START <= start and end <= DAY_END


def validate_class(entry):
    """Check one proposed class on its own, before comparing it to others.

    ``entry`` carries day, start, end (either "HH:MM" or minutes), plus
    teacher, room, batch and subject. Returns a cleaned dict in minutes.
    """
    day = normalise_day(entry.get("day"))
    start = entry.get("start")
    end = entry.get("end")
    start = start if isinstance(start, int) else parse_hhmm(start)
    end = end if isinstance(end, int) else parse_hhmm(end)

    if end <= start:
        raise ClashError("a class must end after it starts")
    length = end - start
    if length < MIN_LESSON:
        raise ClashError("a class of %d minutes is shorter than the %d minute minimum"
                         % (length, MIN_LESSON))
    if length > MAX_LESSON:
        raise ClashError("a class of %d minutes is longer than the %d minute maximum"
                         % (length, MAX_LESSON))
    if not within_college_hours(start, end):
        raise ClashError("%s-%s is outside college hours (%s-%s)"
                         % (fmt_hhmm(start), fmt_hhmm(end),
                            fmt_hhmm(DAY_START), fmt_hhmm(DAY_END)))
    if crosses_lunch(start, end):
        raise ClashError("%s-%s runs into the lunch break (%s-%s)"
                         % (fmt_hhmm(start), fmt_hhmm(end),
                            fmt_hhmm(LUNCH_START), fmt_hhmm(LUNCH_END)))

    out = {"day": day, "start": start, "end": end}
    for field in ("teacher", "room", "batch", "subject"):
        value = str(entry.get(field, "")).strip()
        if not value:
            raise ClashError("a class needs a %s" % field)
        out[field] = value
    return out


def find_clashes(candidate, existing, ignore_id=None):
    """Every reason this class cannot be timetabled against what already exists.

    A resource can only be in one place at a time, and there are three of
    them: the room, the teacher, and the batch of students. Returns a list
    of dicts so the API can tell the user exactly what it collided with -
    "clash" on its own is useless to whoever has to fix the timetable.
    """
    out = []
    for other in existing:
        if ignore_id is not None and other.get("id") == ignore_id:
            continue
        if other["day"] != candidate["day"]:
            continue
        if not overlaps(candidate["start"], candidate["end"],
                        other["start"], other["end"]):
            continue
        for field, label in (("room", "room"), ("teacher", "teacher"),
                             ("batch", "batch")):
            if str(other.get(field, "")).lower() == str(candidate.get(field, "")).lower():
                out.append({
                    "reason": "%s is already booked" % label,
                    "field": field,
                    "value": candidate[field],
                    "clashes_with": other.get("id"),
                    "subject": other.get("subject"),
                    "day": other["day"],
                    "window": "%s-%s" % (fmt_hhmm(other["start"]),
                                         fmt_hhmm(other["end"])),
                    "overlap_minutes": overlap_minutes(
                        candidate["start"], candidate["end"],
                        other["start"], other["end"]),
                })
    return out


def build_views(classes, key):
    """Group classes into a timetable keyed by room, teacher or batch.

    Returns {value: {day: [class, ...]}} with each day sorted by start time,
    which is the shape a template wants and an expensive thing to ask SQL
    for on every page load. This is why the result gets cached.
    """
    if key not in ("room", "teacher", "batch"):
        raise ClashError("can only build a view by room, teacher or batch")
    view = {}
    for c in classes:
        bucket = view.setdefault(str(c[key]), {d: [] for d in DAYS})
        bucket[normalise_day(c["day"])].append({
            "id": c.get("id"),
            "subject": c.get("subject"),
            "start": fmt_hhmm(c["start"]),
            "end": fmt_hhmm(c["end"]),
            "room": c.get("room"),
            "teacher": c.get("teacher"),
            "batch": c.get("batch"),
        })
    for bucket in view.values():
        for day in bucket:
            bucket[day].sort(key=lambda x: x["start"])
    return view


def free_slots(classes, day, minimum=MIN_LESSON):
    """Gaps in a day long enough to put a class in, lunch excluded."""
    day = normalise_day(day)
    busy = sorted((c["start"], c["end"]) for c in classes
                   if normalise_day(c["day"]) == day)
    busy.append((LUNCH_START, LUNCH_END))
    busy.sort()

    merged = []
    for start, end in busy:
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])

    gaps = []
    cursor = DAY_START
    for start, end in merged:
        if start - cursor >= minimum:
            gaps.append({"start": fmt_hhmm(cursor), "end": fmt_hhmm(start),
                         "minutes": start - cursor})
        cursor = max(cursor, end)
    if DAY_END - cursor >= minimum:
        gaps.append({"start": fmt_hhmm(cursor), "end": fmt_hhmm(DAY_END),
                     "minutes": DAY_END - cursor})
    return gaps


def workload(classes):
    """Minutes taught per teacher, so an overloaded timetable is visible."""
    out = {}
    for c in classes:
        out[str(c["teacher"])] = out.get(str(c["teacher"]), 0) + (c["end"] - c["start"])
    return dict(sorted(out.items(), key=lambda kv: (-kv[1], kv[0])))
