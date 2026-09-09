from datetime import datetime, timezone

from fastapi.testclient import TestClient

from flight_tracker.main import app
from flight_tracker.taf import ForecastHour
from flight_tracker.weather import Observation

client = TestClient(app)

WESTERLY = Observation(
    raw="METAR EIDW 071630Z 27015KT 9999 FEW020 14/09 Q1011",
    wind_dir=270,
    wind_speed=15,
)

FORECAST = [
    ForecastHour(datetime(2026, 9, 9, 12, tzinfo=timezone.utc), 280, 10, "28"),
    ForecastHour(datetime(2026, 9, 9, 13, tzinfo=timezone.utc), 210, 7, "16"),
    ForecastHour(datetime(2026, 9, 9, 14, tzinfo=timezone.utc), None, 3, "uncertain"),
]


def _stub_weather(monkeypatch):
    """Replace both network calls, so tests never touch the internet."""
    monkeypatch.setattr("flight_tracker.main.get_observation", lambda: WESTERLY)
    monkeypatch.setattr("flight_tracker.main._current_timeline", lambda: FORECAST)


def test_index_shows_wind_and_inferred_config(monkeypatch):
    _stub_weather(monkeypatch)

    response = client.get("/")

    assert response.status_code == 200
    assert "270" in response.text
    assert "28" in response.text


def test_index_shows_the_forecast_timeline(monkeypatch):
    _stub_weather(monkeypatch)

    response = client.get("/")

    assert "Next 24 hours" in response.text
    assert "slot busy" in response.text    # the 28 hour
    assert "slot quiet" in response.text   # the 16 hour


def test_uncertain_hours_are_flagged_rather_than_guessed(monkeypatch):
    _stub_weather(monkeypatch)

    response = client.get("/")

    assert "slot unknown" in response.text


def test_index_still_renders_when_weather_service_fails(monkeypatch):
    def explode():
        raise RuntimeError("weather service down")

    monkeypatch.setattr("flight_tracker.main.get_observation", explode)
    monkeypatch.setattr("flight_tracker.main._current_timeline", lambda: FORECAST)

    response = client.get("/")

    assert response.status_code == 200
    assert "Could not reach the weather service" in response.text


def test_a_missing_forecast_does_not_cost_us_current_conditions(monkeypatch):
    def explode():
        raise RuntimeError("no TAF today")

    monkeypatch.setattr("flight_tracker.main.get_observation", lambda: WESTERLY)
    monkeypatch.setattr("flight_tracker.main._current_timeline", explode)

    response = client.get("/")

    assert response.status_code == 200
    assert "270" in response.text            # current conditions survived
    assert "Forecast unavailable" in response.text


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
