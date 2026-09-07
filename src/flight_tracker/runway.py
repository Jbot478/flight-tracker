"""Infer Dublin's runway configuration from the surface wind."""

# Dublin's runways and the compass heading each one points along.
# 10L/28R and 10R/28L are the parallel main pair; 16/34 is the crosswind runway.
# Order matters: on an exact tie (a 220 degree wind is equally close to 160
# and 280) the first match wins, and the main runway is the realistic answer.
RUNWAY_HEADINGS = {
    "28": 280,
    "10": 100,
    "34": 340,
    "16": 160,
}

# Below this, the wind isn't strong enough to determine the runway in use.
MIN_DECISIVE_WIND_KT = 5

CONFIG_DESCRIPTIONS = {
    "28": "Departures heading west: expect overhead traffic.",
    "10": "Departures heading east: quiet overhead.",
    "34": "Departures heading northwest on the crosswind runway.",
    "16": "Departures heading southeast on the crosswind runway.",
    "uncertain": "Wind is light or variable: the configuration isn't clear.",
}


def _angular_difference(a: int, b: int) -> int:
    """Smallest angle between two compass bearings, 0-180 degrees."""
    diff = abs(a - b) % 360
    return min(diff, 360 - diff)


def infer_config(wind_dir: int | None, wind_speed: int | None) -> str:
    """Return the runway most likely in use: "28", "10", "34", "16" or "uncertain".

    wind_dir is the direction the wind is coming FROM, in degrees.
    Pass None for a variable-direction wind.
    """
    if wind_dir is None or wind_speed is None:
        return "uncertain"
    if wind_speed < MIN_DECISIVE_WIND_KT:
        return "uncertain"
    return min(
        RUNWAY_HEADINGS,
        key=lambda runway: _angular_difference(RUNWAY_HEADINGS[runway], wind_dir),
    )


def describe_config(config: str) -> str:
    """A plain-English line about what this configuration means on the ground."""
    return CONFIG_DESCRIPTIONS[config]
