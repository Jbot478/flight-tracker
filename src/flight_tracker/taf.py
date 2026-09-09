"""Turn Dublin's TAF forecast into an hour-by-hour runway configuration."""

import re
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone

from flight_tracker.runway import apply_hysteresis, infer_config

# "0912/1012" - day and hour twice: valid from day 09 12:00Z to day 10 12:00Z.
VALIDITY_RE = re.compile(r"\b(\d{2})(\d{2})/(\d{2})(\d{2})\b")

# "091100Z" - when the forecast was issued, as day, hour, minute.
ISSUED_RE = re.compile(r"\b(\d{2})(\d{2})(\d{2})Z\b")

# "28010KT", "22015G26KT", "VRB03KT" - direction, speed, optional gust.
WIND_RE = re.compile(r"\b(\d{3}|VRB)(\d{2,3})(?:G\d{2,3})?KT\b")

# "FM091500" - a sharp change at one moment rather than over a window.
FROM_RE = re.compile(r"\bFM(\d{2})(\d{2})(\d{2})\b")

# The keywords that begin a new group in the body of a TAF.
CHANGE_RE = re.compile(r"\b(BECMG|TEMPO|PROB\d{2}|FM\d{6})")


@dataclass(frozen=True)
class ForecastPeriod:
    """A wind that holds from `start` until the next period begins."""

    start: datetime
    wind_dir: int | None
    wind_speed: int | None


@dataclass(frozen=True)
class ForecastHour:
    """One hour of the timeline shown on the page."""

    time: datetime
    wind_dir: int | None
    wind_speed: int | None
    config: str


@dataclass(frozen=True)
class Forecast:
    raw: str
    issued: datetime
    valid_from: datetime
    valid_to: datetime
    periods: tuple[ForecastPeriod, ...]


def _to_datetime(day: int, hour: int, reference: datetime) -> datetime:
    """A TAF gives day-of-month and hour but no month, so we anchor to the
    issue time and walk forward until the day matches. This handles month
    and year boundaries without any special cases."""
    extra_days, hour = divmod(hour, 24)  # TAFs write midnight as hour 24
    midnight = reference.replace(hour=0, minute=0, second=0, microsecond=0)
    for offset in range(-1, 33):
        candidate = midnight + timedelta(days=offset)
        if candidate.day == day:
            return candidate + timedelta(days=extra_days, hours=hour)
    raise ValueError(f"could not place day {day} near {reference}")


def _issue_time(raw: str, now: datetime) -> datetime:
    match = ISSUED_RE.search(raw)
    if match is None:
        raise ValueError("no issue time in TAF")
    day, hour, minute = (int(part) for part in match.groups())
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    for offset in range(0, -33, -1):
        candidate = midnight + timedelta(days=offset)
        if candidate.day == day:
            return candidate + timedelta(hours=hour, minutes=minute)
    raise ValueError(f"could not place issue day {day}")


def _wind_from(text: str) -> tuple[int | None, int | None]:
    """Direction and speed, or (None, None) if this group has no wind in it."""
    match = WIND_RE.search(text)
    if match is None:
        return None, None
    direction, speed = match.group(1), int(match.group(2))
    if direction == "VRB":
        return None, speed  # variable: no single direction to report
    return int(direction), speed


def _split_groups(body: str) -> list[str]:
    """The base forecast, then one string per change group."""
    starts = [match.start() for match in CHANGE_RE.finditer(body)]
    bounds = [0, *starts, len(body)]
    return [body[bounds[i] : bounds[i + 1]].strip() for i in range(len(bounds) - 1)]


def parse_taf(raw: str, now: datetime | None = None) -> Forecast:
    """Parse a raw TAF into its validity window and a list of wind periods."""
    now = now or datetime.now(timezone.utc)
    body = " ".join(raw.split())

    issued = _issue_time(body, now)

    validity = VALIDITY_RE.search(body)
    if validity is None:
        raise ValueError("no validity window in TAF")
    valid_from = _to_datetime(int(validity.group(1)), int(validity.group(2)), issued)
    valid_to = _to_datetime(int(validity.group(3)), int(validity.group(4)), issued)

    groups = _split_groups(body)

    base_dir, base_speed = _wind_from(groups[0])
    periods = [ForecastPeriod(valid_from, base_dir, base_speed)]

    for group in groups[1:]:
        keyword = group.split()[0]

        # TEMPO and PROB describe brief or unlikely fluctuations. An airport
        # does not turn around for those, so they are not changeovers.
        if keyword.startswith(("TEMPO", "PROB")):
            continue

        wind_dir, wind_speed = _wind_from(group)
        if wind_speed is None:
            continue  # this group changes visibility or cloud, not wind

        if keyword.startswith("FM"):
            match = FROM_RE.search(group)
            start = _to_datetime(int(match.group(1)), int(match.group(2)), issued)
            start += timedelta(minutes=int(match.group(3)))
        else:
            window = VALIDITY_RE.search(group)
            if window is None:
                continue
            # A BECMG window is the transition; the change is complete by
            # the END of it, so that is when the new wind takes effect.
            start = _to_datetime(int(window.group(3)), int(window.group(4)), issued)

        periods.append(ForecastPeriod(start, wind_dir, wind_speed))

    periods.sort(key=lambda period: period.start)
    return Forecast(
        raw=raw,
        issued=issued,
        valid_from=valid_from,
        valid_to=valid_to,
        periods=tuple(periods),
    )


def _period_at(periods: tuple[ForecastPeriod, ...], moment: datetime) -> ForecastPeriod:
    current = periods[0]
    for period in periods:
        if period.start > moment:
            break
        current = period
    return current


def build_timeline(
    forecast: Forecast,
    now: datetime | None = None,
    hours: int = 24,
    hysteresis: bool = True,
) -> list[ForecastHour]:
    """One row per hour from now to the end of the forecast, capped at `hours`.

    With `hysteresis` on (the default) the configurations are smoothed so the
    airport does not appear to swap direction for a marginal wind shift. Turn
    it off to see what the raw wind alone implies.
    """
    now = now or datetime.now(timezone.utc)
    start = max(forecast.valid_from, now.replace(minute=0, second=0, microsecond=0))
    end = min(forecast.valid_to, start + timedelta(hours=hours))

    rows = []
    moment = start
    while moment < end:
        period = _period_at(forecast.periods, moment)
        rows.append(
            ForecastHour(
                time=moment,
                wind_dir=period.wind_dir,
                wind_speed=period.wind_speed,
                config=infer_config(period.wind_dir, period.wind_speed),
            )
        )
        moment += timedelta(hours=1)

    if not hysteresis:
        return rows

    smoothed = apply_hysteresis([(row.wind_dir, row.wind_speed) for row in rows])
    return [replace(row, config=config) for row, config in zip(rows, smoothed)]
