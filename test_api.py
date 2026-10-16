"""End-to-end API tests against real Postgres and Redis."""


def test_health_reports_both_backends(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok", "postgres": True, "redis": True}


def test_add_and_list(client, payload):
    r = client.post("/classes", json=payload())
    assert r.status_code == 201
    assert r.json()["start"] == "10:00"
    listing = client.get("/classes").json()
    assert listing["count"] == 1
    assert listing["teacher_minutes"] == {"Rao": 60}


def test_list_filtered_by_day_and_bad_day(client, payload):
    client.post("/classes", json=payload())
    client.post("/classes", json=payload(day="tue"))
    assert client.get("/classes?day=tue").json()["count"] == 1
    assert client.get("/classes?day=sunday").status_code == 400


def test_partial_overlap_is_refused_with_explanation(client, payload):
    client.post("/classes", json=payload())
    r = client.post("/classes", json=payload(start="10:30", end="11:30"))
    assert r.status_code == 409
    clashes = r.json()["detail"]["clashes"]
    assert {c["field"] for c in clashes} == {"room", "teacher", "batch"}
    assert clashes[0]["overlap_minutes"] == 30
    assert client.get("/classes").json()["count"] == 1  # nothing written


def test_back_to_back_is_accepted(client, payload):
    client.post("/classes", json=payload())
    r = client.post("/classes", json=payload(start="11:00", end="12:00"))
    assert r.status_code == 201


def test_same_slot_other_day_is_accepted(client, payload):
    client.post("/classes", json=payload())
    assert client.post("/classes", json=payload(day="tue")).status_code == 201


def test_different_resources_same_time_is_accepted(client, payload):
    client.post("/classes", json=payload())
    r = client.post("/classes", json=payload(teacher="Iyer", room="B201", batch="CSE-3B"))
    assert r.status_code == 201


def test_lunch_is_refused(client, payload):
    r = client.post("/classes", json=payload(start="12:30", end="13:30"))
    assert r.status_code == 400
    assert "lunch" in r.json()["detail"]


def test_dry_run_writes_nothing(client, payload):
    r = client.post("/classes/check", json=payload())
    assert r.status_code == 200 and r.json()["ok"] is True
    assert client.get("/classes").json()["count"] == 0

    client.post("/classes", json=payload())
    r = client.post("/classes/check", json=payload(start="10:30", end="11:30"))
    assert r.json()["ok"] is False and len(r.json()["clashes"]) == 3


def test_delete_and_404(client, payload):
    cid = client.post("/classes", json=payload()).json()["id"]
    assert client.delete("/classes/%d" % cid).status_code == 200
    assert client.delete("/classes/%d" % cid).status_code == 404


def test_timetable_is_cached_then_served_from_cache(client, payload):
    client.post("/classes", json=payload())
    first = client.get("/timetable/batch/CSE-3A").json()
    second = client.get("/timetable/batch/CSE-3A").json()
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["total_classes"] == 1


def test_add_invalidates_cached_views(client, payload):
    client.post("/classes", json=payload())
    client.get("/timetable/batch/CSE-3A")
    client.get("/timetable/teacher/Rao")
    client.post("/classes", json=payload(start="11:00", end="12:00"))
    for url in ("/timetable/batch/CSE-3A", "/timetable/teacher/Rao"):
        body = client.get(url).json()
        assert body["cached"] is False
        assert body["total_classes"] == 2


def test_delete_invalidates_cached_views(client, payload):
    cid = client.post("/classes", json=payload()).json()["id"]
    assert client.get("/timetable/room/A101").status_code == 200
    client.delete("/classes/%d" % cid)
    assert client.get("/timetable/room/A101").status_code == 404  # no stale deleted class


def test_timetable_bad_kind_and_unknown_value(client):
    assert client.get("/timetable/subject/x").status_code == 400
    assert client.get("/timetable/batch/NOPE").status_code == 404


def test_free_slots(client, payload):
    client.post("/classes", json=payload())
    body = client.get("/free/mon?minutes=60").json()
    spans = [(g["start"], g["end"]) for g in body["free"]]
    assert spans == [("09:00", "10:00"), ("11:00", "13:00"), ("14:00", "17:00")]


def test_free_slots_filtered_and_validation(client, payload):
    client.post("/classes", json=payload())
    body = client.get("/free/mon?teacher=Iyer").json()
    assert body["free"][0]["start"] == "09:00" and body["free"][0]["end"] == "13:00"
    assert client.get("/free/sunday").status_code == 400
    assert client.get("/free/mon?minutes=0").status_code == 400
