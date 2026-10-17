"""Fixtures for API integration tests."""

import os
import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    os.environ.setdefault(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/timetable",
    )
    os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")

    from app.main import app

    with TestClient(app) as test_client:
        yield test_client
