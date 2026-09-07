# Flight Tracker

Predicts Dublin Airport's runway configuration from the current wind, so you can
tell whether departures will be routing overhead.

**Live:** https://flight-tracker-26h3.onrender.com

## Status

| Phase | | |
|---|---|---|
| 1 | Hello World - prove the pipeline | Complete |
| 2 | Live METAR + runway inference | Complete |
| 3 | 24-hour forecast timeline from the TAF | Not started |

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

    uv run pytest        # 15 passed
    uv run ruff check .

Both run automatically in GitHub Actions on every push to main. A red build
blocks the merge.

## Routes

| Route | Returns |
|---|---|
| `/` | HTML: Dublin current wind, the inferred runway configuration, a plain-English summary, and the raw METAR it was derived from |
| `/health` | Status JSON |
| `/docs` | Auto-generated API documentation |

## How it works

**weather.py** fetches the current EIDW METAR from aviationweather.gov (free, no
API key) and parses it with the `metar` library rather than a regex. Dublin
reports carry trailing forecast groups such as `TEMPO 4000 SHRA` that the parser
does not read, so those are stripped before parsing. The result is cached for
five minutes - METARs are only reissued every half hour, so fetching more often
tells us nothing new and needlessly loads a free service.

**runway.py** turns a wind direction and speed into a configuration. Aircraft
take off into the wind, so the runway whose heading is closest to the wind
direction is the one in use: 280 degrees is runway 28, 100 is 10, 340 is 34, 160
is 16. Below 5 knots, or with a variable-direction wind, it returns `uncertain`
rather than inventing a confident answer. Note that a northerly wind favours the
crosswind runway 34, not 10 or 28.

The runway dictionary is deliberately ordered with 28 first. A 220 degree wind is
exactly equidistant from 160 and 280, and Python returns the first match on a
tie - the main runway is the realistic answer. Do not reorder it.

**Tests never touch the network.** Route tests use pytest `monkeypatch` to swap
out the fetch, and the parser tests run against saved real METARs. CI would
otherwise fail whenever aviationweather.gov had a bad minute.

## Deployment

Pushes to main deploy automatically to Render. On the free tier the instance
sleeps when idle, so the first request after a quiet spell takes around 50
seconds - and since the process restarts, the METAR cache starts cold and that
first page load also waits on a live fetch.

## Configuration

Settings use `pydantic-settings`, read from environment variables. `.env.example`
shows the pattern for local overrides. Nothing needs configuring yet; the point
is that there is no temptation to hardcode an API key later.
