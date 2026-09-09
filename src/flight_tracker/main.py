from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from flight_tracker.config import settings
from flight_tracker.runway import describe_config, infer_config
from flight_tracker.taf import ForecastHour, build_timeline, parse_taf
from flight_tracker.weather import Observation, get_observation, get_raw_taf

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app = FastAPI(title=settings.app_name)

# Which colour band each configuration falls into on the timeline.
CONFIG_CLASS = {
    "28": "busy",
    "10": "quiet",
    "16": "quiet",
    "34": "crosswind",
    "uncertain": "unknown",
}


def _describe_wind(observation: Observation) -> str:
    """Turn the numbers into something readable, e.g. '270 at 15 kt'."""
    if observation.wind_speed is None:
        return "not reported"
    if observation.wind_dir is None:
        return f"variable at {observation.wind_speed} kt"
    return f"{observation.wind_dir:03d}\u00b0 at {observation.wind_speed} kt"


def _current_timeline() -> list[ForecastHour]:
    """Fetch, parse and expand the TAF. Kept separate so tests can replace it."""
    return build_timeline(parse_taf(get_raw_taf()))


def _timeline_rows(timeline: list[ForecastHour]) -> list[dict]:
    """Flatten the timeline into what the template needs, so the template
    stays dumb and all the formatting decisions live here."""
    rows = []
    for hour in timeline:
        if hour.wind_dir is None:
            wind = f"variable at {hour.wind_speed} kt"
        else:
            wind = f"{hour.wind_dir:03d} at {hour.wind_speed} kt"
        rows.append(
            {
                "label": hour.time.strftime("%H"),
                "css": CONFIG_CLASS[hour.config],
                "short": "?" if hour.config == "uncertain" else hour.config,
                "detail": f"{hour.time.strftime('%a %H:%M')}Z - {wind} - runway {hour.config}",
            }
        )
    return rows


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    context: dict = {}

    # The weather service is the one part of this we don't control, so a
    # failure there should degrade the page, not break it.
    try:
        observation = get_observation()
    except Exception:
        context["error"] = "Could not reach the weather service just now."
    else:
        config = infer_config(observation.wind_dir, observation.wind_speed)
        context.update(
            {
                "wind": _describe_wind(observation),
                "config": config,
                "summary": describe_config(config),
                "raw": observation.raw,
            }
        )

    # The forecast fails independently: a missing TAF should not cost you
    # the current conditions.
    try:
        context["timeline"] = _timeline_rows(_current_timeline())
    except Exception:
        context["timeline"] = []

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
