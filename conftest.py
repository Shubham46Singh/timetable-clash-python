"""Integration fixtures: a real Postgres and Redis (CircleCI service containers
or `docker compose up postgres redis migrate`). In CI the host is localhost."""
import os

os.environ.setdefault("DATABASE_URL", "postgresql://timetable:timetable@localhost:5432/timetable")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import cache, db  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def clean_state():
    db.query("TRUNCATE classes RESTART IDENTITY", fetch=False)
    cache.client().flushdb()
    yield


@pytest.fixture()
def client():
    return TestClient(app)


@pytest.fixture()
def payload():
    def make(**kw):
        base = {"day": "mon", "start": "10:00", "end": "11:00", "subject": "DBMS",
                "teacher": "Rao", "room": "A101", "batch": "CSE-3A"}
        base.update(kw)
        return base
    return make
