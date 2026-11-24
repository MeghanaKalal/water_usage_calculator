"""Regenerates data/sample_data.csv and data/sample_data.json.

Run from the project root:  python scripts/generate_sample_data.py
Uses a fixed random seed, so the output is the same every time.
"""

import csv
import json
import random
import sys
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from water_calc.models import INPUT_FIELDS  # noqa: E402
from water_calc.validation import record_from_raw  # noqa: E402

random.seed(44)
START = date(2026, 10, 14)


def normal_day(day, size):
    return {
        "date": day.isoformat(), "household_size": size,
        "shower_minutes": round(random.uniform(4, 8) * size, 1),
        "toilet_flushes": random.randint(4, 6) * size // 1,
        "laundry_loads": random.choice([0, 0, 1, 1, 2]),
        "dishwasher_loads": random.choice([0, 1, 1]),
        "dish_wash_minutes": random.choice([0, 5, 10, 15]),
        "garden_minutes": random.choice([0, 0, 0, 10, 20]),
        "car_washes": 0,
        "drinking_cooking_liters": round(random.uniform(3, 6) * size, 1),
        "notes": random.choice(["", "", "Regular weekday", "Quiet day", "Guests for lunch"]),
    }


rows = []
for i in range(38):
    rows.append(normal_day(START + timedelta(days=i), random.choice([3, 4, 4, 4, 5])))

# Hand-made edge cases and boundary values (these make the demo interesting).
edge = [
    {"date": "2026-10-21", "household_size": 1, "shower_minutes": 0, "toilet_flushes": 0,
     "laundry_loads": 0, "dishwasher_loads": 0, "dish_wash_minutes": 0, "garden_minutes": 0,
     "car_washes": 0, "drinking_cooking_liters": 0, "notes": "Away from home - zero usage"},
    {"date": "2026-10-28", "household_size": 20, "shower_minutes": 300, "toilet_flushes": 100,
     "laundry_loads": 10, "dishwasher_loads": 10, "dish_wash_minutes": 120, "garden_minutes": 480,
     "car_washes": 5, "drinking_cooking_liters": 100, "notes": "Maximum boundary values"},
    {"date": "2026-11-04", "household_size": 6, "shower_minutes": 40, "toilet_flushes": 10,
     "laundry_loads": 1, "dishwasher_loads": 0, "dish_wash_minutes": 20, "garden_minutes": 130,
     "car_washes": 1, "drinking_cooking_liters": 8, "notes": "Long garden session + car wash (anomaly)"},
    {"date": "2026-11-10", "household_size": 4, "shower_minutes": 20, "toilet_flushes": 20,
     "laundry_loads": 1, "dishwasher_loads": 1, "dish_wash_minutes": 0, "garden_minutes": 0,
     "car_washes": 0, "drinking_cooking_liters": 12, "notes": "Very efficient day"},
]
# Edge cases replace the normal day that would have fallen on the same date.
edge_dates = {e["date"] for e in edge}
rows = [r for r in rows if r["date"] not in edge_dates]
rows.extend(edge)

# Sort by date, keep JSON (full records) and CSV (inputs only, as a user would export).
rows.sort(key=lambda r: r["date"])
records = []
for number, raw in enumerate(rows, start=1):
    rec = record_from_raw(raw)
    rec.record_id = number
    records.append(rec)

(ROOT / "data").mkdir(exist_ok=True)
with (ROOT / "data" / "sample_data.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=INPUT_FIELDS)
    writer.writeheader()
    writer.writerows(rows)

with (ROOT / "data" / "sample_data.json").open("w", encoding="utf-8") as handle:
    json.dump({"schema_version": 1, "records": [r.to_dict() for r in records]}, handle, indent=2)

print(f"Wrote {len(records)} sample records.")
