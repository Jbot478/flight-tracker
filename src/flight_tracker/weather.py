"""Fetch Dublin's current observation (METAR) and forecast (TAF)."""

import time
from dataclasses import dataclass

import httpx
from metar import Metar

BASE_URL = "https://aviationweather.gov/api/data"
STATION = "EIDW"
REQUEST_TIMEOUT_SECONDS = 10

# METARs are reissued every 30 minutes, TAFs every 6 hours, so re-fetching
# more often than this tells us nothing new and just loads a free service.
CACHE_SECONDS = 300
TAF_CACHE_SECONDS = 1800

# Trailing forecast groups that European METARs carry but the parser doesn't read.
TREND_MARKERS = (" TEMPO ", " BECMG ", " NOSIG")


@dataclass
class Observation:
    """The only three things we need out of a weather report."""

    raw: str
    wind_dir: int | None
    wind_speed: int | None


def _now() -> float:
    """Seconds from an arbitrary start point. A separate function so tests
    can fake the passage of time without actually waiting."""
    return time.monotonic()


class _TimedCache:
    """Remembers one value for a fixed number of seconds."""

    def __init__(self, seconds: int) -> None:
        self.seconds = seconds
        self._value = None
        self._stored_at = 0.0

    def get(self, produce):
        """Return the remembered value, or call `produce` and remember that."""
        moment = _now()
        if self._value is not None and moment - self._stored_at < self.seconds:
            return self._value
        self._value = produce()
        self._stored_at = moment
        return self._value

    def clear(self) -> None:
        self._value = None


_metar_cache = _TimedCache(CACHE_SECONDS)
_taf_cache = _TimedCache(TAF_CACHE_SECONDS)


def _clear_cache() -> None:
    """Forget everything cached. Used by tests."""
    _metar_cache.clear()
    _taf_cache.clear()


def _strip_trend_groups(raw: str) -> str:
    """Cut off the TEMPO/BECMG/NOSIG tail, which describes the near future."""
    for marker in TREND_MARKERS:
        index = raw.find(marker)
        if index != -1:
            raw = raw[:index]
    return raw.strip()


def _fetch(kind: str) -> str:
    response = httpx.get(
        f"{BASE_URL}/{kind}",
        params={"ids": STATION, "format": "raw"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text.strip()


def fetch_raw_metar() -> str:
    """Dublin's latest observation, as plain text."""
    return _fetch("metar")


def fetch_raw_taf() -> str:
    """Dublin's latest forecast, as plain text."""
    return _fetch("taf")


def parse_metar(raw: str) -> Observation:
    """Turn a raw METAR string into an Observation."""
    report = Metar.Metar(_strip_trend_groups(raw), strict=False)

    # A variable-direction wind ("VRB") leaves wind_dir unset, which is the
    # honest answer: there is no single direction to report.
    wind_dir = int(report.wind_dir.value()) if report.wind_dir is not None else None
    wind_speed = int(report.wind_speed.value("KT")) if report.wind_speed is not None else None

    return Observation(raw=raw, wind_dir=wind_dir, wind_speed=wind_speed)


def get_observation() -> Observation:
    """The current observation, re-fetched at most once every CACHE_SECONDS."""
    return _metar_cache.get(lambda: parse_metar(fetch_raw_metar()))


def get_raw_taf() -> str:
    """The current forecast text, re-fetched at most twice an hour."""
    return _taf_cache.get(fetch_raw_taf)
