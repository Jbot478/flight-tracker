"""Download Dublin Airport wind history from the Iowa State ASOS archive.

Free, no API key needed. Writes analysis/data/weather.csv.

This is Part B: throwaway validation code, not part of the deployed app.
"""

from pathlib import Path

import httpx

ASOS_URL = "https://mesonet.agron.iastate.edu/cgi-bin/request/asos.py"
STATION = "EIDW"

# The window from the spec: covers settled easterly spells and Atlantic
# westerlies, so both configurations are well represented.
START = (2026, 4, 1)
END = (2026, 7, 14)  # one day past the 13th, so the 13th is included in full

OUTPUT = Path(__file__).parent / "data" / "weather.csv"


def main() -> None:
    params = {
        "station": STATION,
        "data": "drct,sknt",  # wind direction and speed in knots
        "year1": START[0],
        "month1": START[1],
        "day1": START[2],
        "year2": END[0],
        "month2": END[1],
        "day2": END[2],
        "tz": "Etc/UTC",
        "format": "onlycomma",
        "latlon": "no",
        "missing": "M",
        "trace": "T",
        "direct": "no",
        "report_type": 3,  # routine hourly observations
    }

    print(f"Downloading {STATION} winds, {START} to {END}...")
    print("This can take up to a minute.")
    response = httpx.get(ASOS_URL, params=params, timeout=180)
    response.raise_for_status()

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(response.text, encoding="utf-8")

    lines = response.text.strip().splitlines()
    print()
    print(f"Saved {len(lines) - 1} rows to {OUTPUT}")
    print()
    for line in lines[:4]:
        print("  " + line)


if __name__ == "__main__":
    main()
