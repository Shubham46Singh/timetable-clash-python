"""API integration tests."""

def test_health_endpoint(client):
    response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert "postgres" in data
    assert "redis" in data


def test_list_classes_endpoint(client):
    response = client.get("/classes")

    assert response.status_code == 200

    data = response.json()

    assert isinstance(data, dict)
    assert "count" in data
    assert "classes" in data
    assert "teacher_minutes" in data

    assert isinstance(data["classes"], list)
    assert data["count"] == len(data["classes"])
