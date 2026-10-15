from fastapi.testclient import TestClient

from app.main import app, db, cache

client = TestClient(app)


def test_health_ok(monkeypatch):
    monkeypatch.setattr(db, "query", lambda *a, **k: [{"value": 1}])

    class RedisMock:
        def ping(self):
            return True

    monkeypatch.setattr(cache, "client", lambda: RedisMock())

    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["postgres"] is True
    assert response.json()["redis"] is True


def test_health_database_failure(monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(db, "query", fail)

    class RedisMock:
        def ping(self):
            return True

    monkeypatch.setattr(cache, "client", lambda: RedisMock())

    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["postgres"] is False


def test_health_redis_failure(monkeypatch):
    monkeypatch.setattr(db, "query", lambda *a, **k: [])

    def fail():
        raise RuntimeError("redis unavailable")

    monkeypatch.setattr(cache, "client", fail)

    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["redis"] is False


def test_list_classes_empty(monkeypatch):
    monkeypatch.setattr(db, "query", lambda *a, **k: [])
    response = client.get("/classes")
    assert response.status_code == 200
    assert response.json()["count"] == 0


def test_list_classes_invalid_day():
    response = client.get("/classes?day=Funday")
    assert response.status_code == 400


def test_dry_run_invalid_class():
    response = client.post("/classes/check", json={})
    assert response.status_code == 400


def test_add_class_invalid_class():
    response = client.post("/classes", json={})
    assert response.status_code == 400


def test_delete_missing_class():
    response = client.delete("/classes/99999")
    assert response.status_code == 404


def test_timetable_invalid_kind():
    response = client.get("/timetable/student/ISE")
    assert response.status_code == 400


def test_timetable_missing_value(monkeypatch):
    monkeypatch.setattr(db, "query", lambda *a, **k: [])
    response = client.get("/timetable/batch/ISE")
    assert response.status_code == 404


def test_free_invalid_day():
    response = client.get("/free/Funday")
    assert response.status_code == 400


def test_free_invalid_minutes():
    response = client.get("/free/Monday?minutes=0")
    assert response.status_code == 400
