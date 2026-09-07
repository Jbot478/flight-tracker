from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from flight_tracker.config import settings
from flight_tracker.runway import describe_config, infer_config
from flight_tracker.weather import Observation, get_observation

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=BASE_DIR / "templates")

app = FastAPI(title=settings.app_name)


def _describe_wind(observation: Observation) -> str:
    """Turn the numbers into something readable, e.g. '270 at 15 kt'."""
    if observation.wind_speed is None:
        return "not reported"
    if observation.wind_dir is None:
        return f"variable at {observation.wind_speed} kt"
    return f"{observation.wind_dir:03d}\u00b0 at {observation.wind_speed} kt"


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    # The weather service is the one part of this we don't control, so a
    # failure there should degrade the page, not break it.
    try:
        observation = get_observation()
    except Exception:
        context = {"error": "Could not reach the weather service just now."}
    else:
        config = infer_config(observation.wind_dir, observation.wind_speed)
        context = {
            "wind": _describe_wind(observation),
            "config": config,
            "summary": describe_config(config),
            "raw": observation.raw,
        }

    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context=context,
    )


@app.get("/health")
def health():
    return {"status": "ok"}
