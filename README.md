# Flight Tracker

Predicts Dublin Airport (EIDW) runway configuration from wind conditions, to
estimate when aircraft will be overhead.

**Live:** https://flight-tracker-26h3.onrender.com

## Status

Phase 1 complete: deployed hello world, proving the full pipeline
(local → GitHub → CI → Render).

Next up — Phase 2: fetch live EIDW METAR, parse the wind, infer runway config.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) (installs Python for you)
- git

## Running locally

```bash
git clone https://github.com/Jbot478/flight-tracker.git
cd flight-tracker
uv sync
uv run uvicorn flight_tracker.main:app --reload
```

Then open http://127.0.0.1:8000

## Routes

| Route | Returns |
|---|---|
| `/` | HTML greeting |
| `/health` | `{"status": "ok"}` |
| `/docs` | Auto-generated API docs |

## Tests and linting

```bash
uv run pytest
uv run ruff check .
uv run ruff format .
```

CI runs ruff and pytest on every push to main.

## Deployment

Auto-deploys to Render on push to `main`.

- Build: `pip install uv && uv sync --frozen`
- Start: `uv run uvicorn flight_tracker.main:app --host 0.0.0.0 --port $PORT`

Free tier spins down when idle, so the first request after a quiet spell can
take ~50 seconds.

## Configuration

Config is read from environment variables via `pydantic-settings`
(`src/flight_tracker/config.py`). Copy `.env.example` to `.env` for local
overrides. Nothing is required yet — the pattern exists so API keys don't get
hardcoded in Phase 2.