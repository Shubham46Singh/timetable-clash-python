
"""API integration test template for FastAPI."""

import pytest
from fastapi.testclient import TestClient

# Change this import to the module that creates your FastAPI app.
from app.main import app


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def test_health_endpoint(client):
    # Replace /health with an endpoint that actually exists.
    response = client.get("/health")

    assert response.status_code == 200
