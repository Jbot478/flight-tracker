"""How much room is there in the two thresholds we guessed at?

MAX_CROSSWIND_KT decides when the crosswind runway comes into play.
A tailwind tolerance would decide when Dublin holds 28 through a light easterly.
Both were set by judgement. This measures what the actual wind record supports.
"""

import csv
from pathlib import Path

from flight_tracker.runway import crosswind, headwind, infer_config

WEATHER = Path(__file__).parent / "data" / "weather.csv"


def load():
    rows = []
    with WEATHER.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            raw_dir, raw_speed = record["drct"], record["sknt"]
            if raw_dir in ("M", "") or raw_speed in ("M", ""):
                continue
            rows.append((int(float(raw_dir)), int(float(raw_speed))))
    return rows


def main() -> None:
    rows = load()
    total = len(rows)
    print(f"{total} hours with a usable wind reading")
    print()

    # How square across the parallel runways does the wind actually get?
    crosswinds = [crosswind(d, s, "28") for d, s in rows]
    print(f"  Strongest crosswind on 10/28 in the period: {max(crosswinds):.1f} kt")
    print()
    print("  Hours above each possible crosswind limit:")
    for limit in (15, 20, 25, 30):
        above = sum(1 for value in crosswinds if value > limit)
        print(f"    over {limit:>2} kt   {above:>5}  {100 * above / total:5.1f}%")
    print()

    # When we call it easterly, how marginal is that call? If runway 28 would
    # only have a light tailwind, Dublin might well have stayed on 28.
    easterly = [(d, s) for d, s in rows if infer_config(d, s) == "10"]
    print(f"  Hours scored as runway 10: {len(easterly)} "
          f"({100 * len(easterly) / total:.1f}%)")
    print()
    print("  ...of which runway 28 would have had a tailwind of only:")
    for limit in (3, 5, 7, 10):
        marginal = sum(1 for d, s in easterly if -headwind(d, s, "28") <= limit)
        print(f"    under {limit:>2} kt  {marginal:>5}  "
              f"{100 * marginal / total:5.1f}% of all hours")


if __name__ == "__main__":
    main()
