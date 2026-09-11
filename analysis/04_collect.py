"""Record which aircraft are over Coolquoy, and when.

Part B ground truth. Polls OpenSky for a small bounding box every POLL_SECONDS
for a burst of a few minutes, then exits. Meant to be run on a schedule: each
run appends a handful of rows.

Needs OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET in the environment, or in a
local .env file. Never commit those.

Usage:  python analysis/04_collect.py [burst_seconds]
"""

import csv
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
STATES_URL = "https://opensky-network.org/api/states/all"

# A 3 km box around Coolquoy Lodge (53.4589 N, 6.3495 W).
BOX = {"lamin": 53.4454, "lamax": 53.4724, "lomin": -6.3721, "lomax": -6.3269}

# Departures climbing out. Above this is unrelated high-level overflying.
MAX_ALTITUDE_FT = 7000
FEET_PER_METRE = 3.28084

POLL_SECONDS = 20
DEFAULT_BURST_SECONDS = 300

OBSERVATIONS = Path(__file__).parent / "observations"
POLLS_CSV = OBSERVATIONS / "polls.csv"
SIGHTINGS_CSV = OBSERVATIONS / "sightings.csv"

POLL_FIELDS = ["time", "aircraft_in_box", "aircraft_below_limit", "credits_remaining"]
SIGHTING_FIELDS = [
    "time", "icao24", "callsign", "lat", "lon", "altitude_ft", "track", "vertical_rate"
]


def load_dotenv() -> None:
    """Read a local .env if there is one. Keeps secrets out of the code."""
    path = Path(__file__).resolve().parents[1] / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def get_token(client_id: str, client_secret: str) -> str:
    """OpenSky uses OAuth2 client credentials. Tokens last 30 minutes, which
    comfortably covers one burst."""
    response = httpx.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": client_id,
            "client_secret": client_secret,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]


def poll(token: str) -> tuple[list[dict], str | None]:
    """Everything airborne inside the box right now, plus credits left today."""
    response = httpx.get(
        STATES_URL,
        params=BOX,
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    response.raise_for_status()
    remaining = response.headers.get("X-Rate-Limit-Remaining")

    aircraft = []
    for state in response.json().get("states") or []:
        if state[8]:  # on_ground
            continue
        altitude_m = state[13] if state[13] is not None else state[7]
        aircraft.append(
            {
                "icao24": state[0],
                "callsign": (state[1] or "").strip(),
                "lat": state[6],
                "lon": state[5],
                "altitude_ft": (
                    round(altitude_m * FEET_PER_METRE) if altitude_m is not None else None
                ),
                "track": state[10],
                "vertical_rate": state[11],
            }
        )
    return aircraft, remaining


def append(path: Path, fields: list[str], rows: list[dict]) -> None:
    if not rows:
        return
    new_file = not path.exists()
    with path.open("a", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if new_file:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    burst = int(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_BURST_SECONDS

    load_dotenv()
    client_id = os.environ.get("OPENSKY_CLIENT_ID")
    client_secret = os.environ.get("OPENSKY_CLIENT_SECRET")
    if not client_id or not client_secret:
        raise SystemExit(
            "Set OPENSKY_CLIENT_ID and OPENSKY_CLIENT_SECRET (in .env or the environment)"
        )

    token = get_token(client_id, client_secret)
    OBSERVATIONS.mkdir(parents=True, exist_ok=True)

    polls: list[dict] = []
    sightings: list[dict] = []
    last_remaining = None

    print(f"Watching the box for {burst}s, one look every {POLL_SECONDS}s")
    started = time.monotonic()
    while time.monotonic() - started < burst:
        stamp = datetime.now(timezone.utc)
        when = stamp.strftime("%Y-%m-%d %H:%M:%S")

        try:
            airborne, remaining = poll(token)
        except httpx.HTTPError as error:
            print(f"  {when}  poll failed: {error}")
            time.sleep(POLL_SECONDS)
            continue

        last_remaining = remaining
        low = [
            plane
            for plane in airborne
            if plane["altitude_ft"] is not None
            and plane["altitude_ft"] <= MAX_ALTITUDE_FT
        ]

        polls.append(
            {
                "time": when,
                "aircraft_in_box": len(airborne),
                "aircraft_below_limit": len(low),
                "credits_remaining": remaining,
            }
        )
        for plane in low:
            sightings.append({"time": when, **plane})

        note = ", ".join(
            f"{plane['callsign'] or plane['icao24']} {plane['altitude_ft']}ft"
            for plane in low
        )
        print(
            f"  {when}  {len(airborne)} in box, {len(low)} low"
            f"{' - ' + note if note else ''}   [credits left: {remaining}]"
        )

        time.sleep(POLL_SECONDS)

    append(POLLS_CSV, POLL_FIELDS, polls)
    append(SIGHTINGS_CSV, SIGHTING_FIELDS, sightings)
    print()
    print(f"{len(polls)} polls, {len(sightings)} sightings appended")
    print(f"Credits remaining today: {last_remaining}")


if __name__ == "__main__":
    main()
