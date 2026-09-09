"""What runway configuration was Dublin in, hour by hour, April to July?

Runs the archive winds through the same infer_config and apply_hysteresis
the live site uses. No aircraft data yet: this is just what the model claims.
"""

import csv
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from flight_tracker.runway import apply_hysteresis, infer_config

DATA = Path(__file__).parent / "data"
WEATHER = DATA / "weather.csv"
OUTPUT = DATA / "runway_history.csv"

# The spec's threshold for a wind decisive enough that we expect the model
# to be right. Anything below this is where the risk lives.
DECISIVE_KT = 8


def load_rows() -> list[tuple[datetime, int | None, int | None]]:
    rows = []
    with WEATHER.open(newline="", encoding="utf-8") as handle:
        for record in csv.DictReader(handle):
            stamp = datetime.strptime(record["valid"], "%Y-%m-%d %H:%M")
            stamp = stamp.replace(tzinfo=timezone.utc)
            raw_dir, raw_speed = record["drct"], record["sknt"]
            wind_dir = int(float(raw_dir)) if raw_dir not in ("M", "") else None
            wind_speed = int(float(raw_speed)) if raw_speed not in ("M", "") else None
            rows.append((stamp, wind_dir, wind_speed))
    return rows


def share(counter: Counter, total: int) -> str:
    lines = []
    for config, count in counter.most_common():
        lines.append(f"    {config:<10} {count:>5}  {100 * count / total:5.1f}%")
    return "\n".join(lines)


def count_changeovers(configs: list[str]) -> int:
    return sum(1 for a, b in zip(configs, configs[1:]) if a != b)


def main() -> None:
    rows = load_rows()
    total = len(rows)
    winds = [(wind_dir, wind_speed) for _, wind_dir, wind_speed in rows]

    raw = [infer_config(wind_dir, wind_speed) for wind_dir, wind_speed in winds]
    smoothed = apply_hysteresis(winds)

    print(f"{total} hours, {rows[0][0].date()} to {rows[-1][0].date()}")
    print()

    print("  Raw (nearest runway heading):")
    print(share(Counter(raw), total))
    print()

    print("  Smoothed (with hysteresis):")
    print(share(Counter(smoothed), total))
    print()

    disagreements = sum(1 for a, b in zip(raw, smoothed) if a != b)
    print(f"  Hysteresis changed the answer in {disagreements} hours "
          f"({100 * disagreements / total:.1f}%)")
    print(f"  Changeovers, raw:      {count_changeovers(raw)}")
    print(f"  Changeovers, smoothed: {count_changeovers(smoothed)}")
    print()

    decisive = [
        config
        for config, (_, speed) in zip(smoothed, winds)
        if speed is not None and speed > DECISIVE_KT
    ]
    print(f"  Decisive-wind hours (over {DECISIVE_KT} kt): {len(decisive)} "
          f"({100 * len(decisive) / total:.1f}% of the period)")
    print(share(Counter(decisive), len(decisive)))
    print()

    with OUTPUT.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["valid", "wind_dir", "wind_speed", "config_raw", "config"])
        for (stamp, wind_dir, wind_speed), raw_c, smooth_c in zip(rows, raw, smoothed):
            writer.writerow(
                [stamp.strftime("%Y-%m-%d %H:%M"), wind_dir, wind_speed, raw_c, smooth_c]
            )
    print(f"  Hourly configurations written to {OUTPUT}")


if __name__ == "__main__":
    main()
