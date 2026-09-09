# Flight Tracker

Predicts Dublin Airport's runway configuration from wind, so you can tell
whether departures will be routing overhead - now, and for the next 24 hours.

**Live:** https://flight-tracker-26h3.onrender.com

## Status

| Phase | | |
|---|---|---|
| 1 | Hello World - prove the pipeline | Complete |
| 2 | Live METAR + runway inference | Complete |
| 3 | 24-hour forecast timeline from the TAF | Complete |

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (it installs and manages Python for you)
- git

## Local development

    git clone https://github.com/Jbot478/flight-tracker.git
    cd flight-tracker
    uv sync
    uv run uvicorn flight_tracker.main:app --reload

Then open http://127.0.0.1:8000

Note the module path: it is **flight_tracker.main:app**, not `main:app` and not
`app.main:app`. The package lives under `src/flight_tracker/`, so the importable
name is `flight_tracker.main`. This is the single most likely thing to trip you
up when coming back to the project.

## Tests and linting

    uv run pytest        # 37 passed
    uv run ruff check .

Both run automatically in GitHub Actions on every push to main. A red build
blocks the merge.

## Routes

| Route | Returns |
|---|---|
| `/` | HTML: current wind and inferred runway, plus an hour-by-hour predicted configuration for the next 24 hours |
| `/health` | Status JSON |
| `/docs` | Auto-generated API documentation |

## How it works

**weather.py** fetches the current METAR and the current TAF for EIDW from
aviationweather.gov (free, no API key). METARs are parsed with the `metar`
library rather than a regex; trailing trend groups such as `TEMPO 4000 SHRA`
are stripped first, because the library does not read them. Results are cached
- five minutes for the observation, thirty for the forecast - since neither is
reissued more often than that.

**runway.py** turns a wind into a configuration. Aircraft take off into the
wind, so the runway whose heading is closest to the wind direction is the one in
use: 280 degrees is runway 28, 100 is 10, 340 is 34, 160 is 16. Below 5 knots,
or with a variable wind, it returns `uncertain` rather than inventing a
confident answer. A northerly wind favours the crosswind runway 34, not 10 or 28.

The runway dictionary is deliberately ordered with 28 first. A 220 degree wind is
exactly equidistant from 160 and 280, and Python returns the first match on a
tie - the main runway is the realistic answer. Do not reorder it.

**taf.py** parses the forecast into a timeline. A TAF gives a base wind plus
`BECMG` change groups; a BECMG window is the transition, so the new wind takes
effect at the END of it. `TEMPO` and `PROB30` groups are ignored entirely -
they describe brief or unlikely fluctuations, and an airport does not turn
around for those. The `metar` library does not handle TAFs, so this parser is
written from scratch.

**Hysteresis.** A changeover stops departures and turns every aircraft around,
so the raw "nearest heading" answer is too eager. `apply_hysteresis` only
switches when the new runway gains at least 5 knots of headwind over the
current one, and only once that has held for two consecutive hours. A 210
degree wind at 7 knots gains runway 16 barely 2 knots over runway 28, so the
airport holds. A 160 degree wind at 8 knots leaves runway 28 with a tailwind,
so it switches. Pass `hysteresis=False` to `build_timeline` to see the raw
wind-only answer; both behaviours are pinned by tests.

**Tests never touch the network.** Route tests use pytest `monkeypatch` to swap
out the fetches; the parsers are tested against saved real METARs and TAFs,
including a messy TAF with a `PROB30 TEMPO`.

## Deployment

Pushes to main deploy automatically to Render. On the free tier the instance
sleeps when idle, so the first request after a quiet spell takes around 50
seconds - and since the process restarts, the caches start cold and that first
page load also waits on live fetches.

## Configuration

Settings use `pydantic-settings`, read from environment variables. `.env.example`
shows the pattern for local overrides. Nothing needs configuring yet; the point
is that there is no temptation to hardcode an API key later.
