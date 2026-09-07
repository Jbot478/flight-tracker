from fastapi.testclient import TestClient

from flight_tracker.main import app
from flight_tracker.weather import Observation

client = TestClient(app)

WESTERLY = Observation(
    raw="METAR EIDW 071630Z 27015KT 9999 FEW020 14/09 Q1011",
    wind_dir=270,
    wind_speed=15,
)


def test_index_shows_wind_and_inferred_config(monkeypatch):
    # Replace the real network call with a fixed observation, so this test
    # never touches the internet and always gives the same answer.
    monkeypatch.setattr("flight_tracker.main.get_observation", lambda: WESTERLY)

    response = client.get("/")

    assert response.status_code == 200
    assert "270" in response.text
    assert "28" in response.text


def test_index_still_renders_when_weather_service_fails(monkeypatch):
    def explode():
        raise RuntimeError("weather service down")

    monkeypatch.setattr("flight_tracker.main.get_observation", explode)

    response = client.get("/")

    assert response.status_code == 200
    assert "Could not reach the weather service" in response.text


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
