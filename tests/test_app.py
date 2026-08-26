from fastapi.testclient import TestClient

from flight_tracker.main import app

client = TestClient(app)


def test_index_returns_greeting():
    response = client.get("/")
    assert response.status_code == 200
    assert "Hello: Flight Tracker" in response.text


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
