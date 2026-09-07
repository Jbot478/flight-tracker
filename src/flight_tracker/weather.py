"""Fetch and parse the current METAR observation for Dublin Airport (EIDW)."""

from dataclasses import dataclass

import httpx
from metar import Metar

METAR_URL = "https://aviationweather.gov/api/data/metar"
STATION = "EIDW"
REQUEST_TIMEOUT_SECONDS = 10

# Trailing forecast groups that European METARs carry but the parser doesn't read.
TREND_MARKERS = (" TEMPO ", " BECMG ", " NOSIG")


@dataclass
class Observation:
    """The only three things we need out of a weather report."""

    raw: str
    wind_dir: int | None
    wind_speed: int | None


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
    """Fetch and parse in one call. This is what the web page uses."""
    return parse_metar(fetch_raw_metar())
