"""Fetch and parse the current METAR observation for Dublin Airport (EIDW)."""

import time
from dataclasses import dataclass

import httpx
from metar import Metar

METAR_URL = "https://aviationweather.gov/api/data/metar"
STATION = "EIDW"
REQUEST_TIMEOUT_SECONDS = 10

# METARs are only reissued every 30 minutes, so re-fetching more often than
# this tells us nothing new and just loads someone else's free service.
CACHE_SECONDS = 300

# Trailing forecast groups that European METARs carry but the parser doesn't read.
TREND_MARKERS = (" TEMPO ", " BECMG ", " NOSIG")


@dataclass
class Observation:
    """The only three things we need out of a weather report."""

    raw: str
    wind_dir: int | None
    wind_speed: int | None


# The most recent observation and when we got it, or None if we have neither.
_cached: tuple[float, Observation] | None = None


def _now() -> float:
    """Seconds from an arbitrary start point. A separate function so tests
    can fake the passage of time without actually waiting."""
    return time.monotonic()


def _clear_cache() -> None:
    """Forget the cached observation. Used by tests."""
    global _cached
    _cached = None


def _strip_trend_groups(raw: str) -> str:
    """Cut off the TEMPO/BECMG/NOSIG tail, which describes the near future."""
    for marker in TREND_MARKERS:
        index = raw.find(marker)
        if index != -1:
            raw = raw[:index]
    return raw.strip()


def fetch_raw_metar() -> str:
    """Ask aviationweather.gov for Dublin's latest observation, as plain text."""
    response = httpx.get(
        METAR_URL,
        params={"ids": STATION, "format": "raw"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.text.strip()


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
    global _cached

    now = _now()
    if _cached is not None and now - _cached[0] < CACHE_SECONDS:
        return _cached[1]

    observation = parse_metar(fetch_raw_metar())
    _cached = (now, observation)
    return observation
