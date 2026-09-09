"""Infer Dublin's runway configuration from the surface wind."""

import math

# Dublin's runways and the compass heading each one points along.
RUNWAY_HEADINGS = {
    "28": 280,
    "10": 100,
    "34": 340,
    "16": 160,
}

# 10L/28R and 10R/28L are the parallel pair, and Dublin strongly prefers them:
# twice the capacity, and the taxiways and procedures are built around them.
# 16/34 is the crosswind runway, used only when the wind makes the parallels
# genuinely unsuitable. Order matters within each pair - on an exact tie the
# first wins, and westerly operations are Dublin's usual case.
MAIN_PAIR = ("28", "10")
CROSSWIND_PAIR = ("34", "16")

# Below this, the wind isn't strong enough to determine the runway in use.
MIN_DECISIVE_WIND_KT = 5

# Roughly what large jets accept across a dry runway. Beyond it the crosswind
# runway becomes the sensible option. A starting figure, to be tuned against
# real traffic rather than trusted.
MAX_CROSSWIND_KT = 25

# A changeover stops departures and turns every aircraft around, so the new
# runway has to be meaningfully better - not just marginally nearer the wind.
CHANGEOVER_MARGIN_KT = 5

# ...and it has to stay better this many hours running, so a brief shift
# cannot flip the prediction.
CHANGEOVER_MIN_HOURS = 2

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


def headwind(wind_dir: int, wind_speed: int, runway: str) -> float:
    """Knots of headwind a runway gets from this wind. Negative is a tailwind."""
    offset = _angular_difference(RUNWAY_HEADINGS[runway], wind_dir)
    return wind_speed * math.cos(math.radians(offset))


def crosswind(wind_dir: int, wind_speed: int, runway: str) -> float:
    """Knots of wind blowing across the runway rather than along it."""
    offset = _angular_difference(RUNWAY_HEADINGS[runway], wind_dir)
    return abs(wind_speed * math.sin(math.radians(offset)))


def _best_of(pair: tuple[str, ...], wind_dir: int, wind_speed: int) -> str:
    """Whichever end of a runway gives a headwind rather than a tailwind."""
    return max(pair, key=lambda runway: headwind(wind_dir, wind_speed, runway))


def infer_config(wind_dir: int | None, wind_speed: int | None) -> str:
    """Return the runway most likely in use: "28", "10", "34", "16" or "uncertain".

    Dublin prefers the parallel pair and only uses the crosswind runway when
    the crosswind on the parallels becomes unmanageable.

    wind_dir is the direction the wind is coming FROM, in degrees.
    Pass None for a variable-direction wind.
    """
    if wind_dir is None or wind_speed is None:
        return "uncertain"
    if wind_speed < MIN_DECISIVE_WIND_KT:
        return "uncertain"

    main = _best_of(MAIN_PAIR, wind_dir, wind_speed)
    if crosswind(wind_dir, wind_speed, main) <= MAX_CROSSWIND_KT:
        return main
    return _best_of(CROSSWIND_PAIR, wind_dir, wind_speed)


def infer_config_nearest(wind_dir: int | None, wind_speed: int | None) -> str:
    """The original rule: whichever runway heading is nearest the wind.

    Kept for comparison. It treats all four runways as equal candidates, which
    sends Dublin to the crosswind runway far more often than really happens.
    """
    if wind_dir is None or wind_speed is None:
        return "uncertain"
    if wind_speed < MIN_DECISIVE_WIND_KT:
        return "uncertain"
    return min(
        RUNWAY_HEADINGS,
        key=lambda runway: _angular_difference(RUNWAY_HEADINGS[runway], wind_dir),
    )


def _worth_switching(
    wind_dir: int | None,
    wind_speed: int | None,
    current: str,
    candidate: str,
) -> bool:
    """Would changing to `candidate` buy enough headwind to justify the upheaval?"""
    if wind_dir is None or wind_speed is None:
        return False
    if current not in RUNWAY_HEADINGS:
        return True  # nothing established to protect
    gain = headwind(wind_dir, wind_speed, candidate) - headwind(
        wind_dir, wind_speed, current
    )
    return gain >= CHANGEOVER_MARGIN_KT


def apply_hysteresis(
    winds: list[tuple[int | None, int | None]],
    current: str | None = None,
) -> list[str]:
    """Smooth a run of hourly winds into the configurations an airport would
    plausibly actually use, rather than flipping on every marginal shift."""
    configs: list[str] = []
    pending: str | None = None
    pending_hours = 0

    for wind_dir, wind_speed in winds:
        candidate = infer_config(wind_dir, wind_speed)

        # Nothing established yet: take the reading at face value.
        if current is None or current == "uncertain":
            current = candidate
            pending, pending_hours = None, 0
            configs.append(current)
            continue

        if candidate == current or candidate == "uncertain":
            # No pressure to change, so any building case dissolves.
            pending, pending_hours = None, 0
        elif _worth_switching(wind_dir, wind_speed, current, candidate):
            pending_hours = pending_hours + 1 if candidate == pending else 1
            pending = candidate
            if pending_hours >= CHANGEOVER_MIN_HOURS:
                current = candidate
                pending, pending_hours = None, 0
        else:
            pending, pending_hours = None, 0

        configs.append(current)

    return configs


def describe_config(config: str) -> str:
    """A plain-English line about what this configuration means on the ground."""
    return CONFIG_DESCRIPTIONS[config]
