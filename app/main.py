
from fastapi import Body, FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from . import cache, db
from .clashes import (
    DAYS,
    ClashError,
    build_views,
    find_clashes,
    fmt_hhmm,
    free_slots,
    normalise_day,
    validate_class,
    workload,
)

app = FastAPI()


@app.get("/")
def root():
    return {
        "service": "timetable-clash",
        "docs": "/docs",
        "health": "/health",
    }


COLS = 'id, day, start_min AS start, end_min AS "end", subject, teacher, room, batch'


@app.get("/health")
def health():
    out = {"status": "ok", "postgres": False, "redis": False}

    try:
        db.query("SELECT 1")
        out["postgres"] = True
    except Exception as e:
        out["pg_error"] = str(e)

    try:
        cache.client().ping()
        out["redis"] = True
    except Exception as e:
        out["redis_error"] = str(e)

    return (
        out
        if out["postgres"] and out["redis"]
        else JSONResponse(out, status_code=503)
    )


def all_classes():
    return db.query(
        "SELECT " + COLS + " FROM classes ORDER BY day, start_min, id"
    )


def readable(row):
    out = dict(row)
    out["start"] = fmt_hhmm(row["start"])
    out["end"] = fmt_hhmm(row["end"])
    return out


def check(payload, ignore_id=None):
    """Validate one class and compare it against everything already booked."""
    try:
        entry = validate_class(payload)
    except ClashError as e:
        raise HTTPException(400, str(e))

    return entry, find_clashes(entry, all_classes(), ignore_id=ignore_id)


@app.get("/classes")
def list_classes(day: str = Query(None)):
    rows = all_classes()

    if day:
        try:
            day = normalise_day(day)
        except ClashError as e:
            raise HTTPException(400, str(e))

        rows = [r for r in rows if r["day"] == day]

    return {
        "count": len(rows),
        "classes": [readable(r) for r in rows],
        "teacher_minutes": workload(all_classes()),
    }


@app.post("/classes/check")
def dry_run(payload: dict = Body(...)):
    """Would this class be accepted? Nothing is written either way."""
    entry, clashes = check(payload)

    return {
        "ok": not clashes,
        "slot": "%s %s-%s"
        % (
            entry["day"],
            fmt_hhmm(entry["start"]),
            fmt_hhmm(entry["end"]),
        ),
        "clashes": clashes,
    }


@app.post("/classes", status_code=201)
def add_class(payload: dict = Body(...)):
    entry, clashes = check(payload)

    if clashes:
        raise HTTPException(
            409,
            {"error": "that slot clashes", "clashes": clashes},
        )

    row = db.one(
        "INSERT INTO classes "
        "(day, start_min, end_min, subject, teacher, room, batch)"
        " VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING " + COLS,
        (
            entry["day"],
            entry["start"],
            entry["end"],
            entry["subject"],
            entry["teacher"],
            entry["room"],
            entry["batch"],
        ),
    )

    cache.drop_prefix("tt:")
    return readable(row)


@app.delete("/classes/{cid}")
def delete_class(cid: int):
    row = db.one(
        "DELETE FROM classes WHERE id=%s RETURNING " + COLS,
        (cid,),
    )

    if not row:
        raise HTTPException(404, "no class with id %d" % cid)

    cache.drop_prefix("tt:")
    return {"deleted": readable(row)}


@app.get("/timetable/{kind}/{value}")
def timetable(kind: str, value: str):
    if kind not in ("batch", "teacher", "room"):
        raise HTTPException(400, "kind must be batch, teacher or room")

    key = "tt:%s:%s" % (kind, value)
    hit = cache.get_json(key)

    if hit:
        return {**hit, "cached": True}

    views = build_views(all_classes(), kind)

    if value not in views:
        raise HTTPException(
            404,
            "no classes for %s %r" % (kind, value),
        )

    out = {
        "kind": kind,
        "value": value,
        "days": views[value],
        "total_classes": sum(len(v) for v in views[value].values()),
    }

    cache.set_json(key, out, ttl=600)
    return {**out, "cached": False}


@app.get("/free/{day}")
def free(
    day: str,
    minutes: int = Query(60),
    room: str = Query(None),
    teacher: str = Query(None),
    batch: str = Query(None),
):
    """Where could a class actually go? Filter by whichever resource is scarce."""
    try:
        day = normalise_day(day)
    except ClashError as e:
        raise HTTPException(400, str(e))

    rows = all_classes()

    for field, want in (
        ("room", room),
        ("teacher", teacher),
        ("batch", batch),
    ):
        if want:
            rows = [r for r in rows if r[field] == want]

    if minutes < 1:
        raise HTTPException(400, "minutes must be positive")

    return {
        "day": day,
        "minimum_minutes": minutes,
        "filtered_by": {
            "room": room,
            "teacher": teacher,
            "batch": batch,
        },
        "free": free_slots(rows, day, minimum=minutes),
        "teaching_days": list(DAYS),
    }
