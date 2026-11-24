"""The one data structure the whole app revolves around: a day of water use."""

from dataclasses import dataclass, asdict

# The things a person actually types in (also the columns of an import CSV).
INPUT_FIELDS = [
    "date",
    "household_size",
    "shower_minutes",
    "toilet_flushes",
    "laundry_loads",
    "dishwasher_loads",
    "dish_wash_minutes",
    "garden_minutes",
    "car_washes",
    "drinking_cooking_liters",
    "notes",
]

# Everything we store / export.
ALL_FIELDS = ["record_id"] + INPUT_FIELDS + ["total_liters", "per_person_liters", "status"]


@dataclass
class UsageRecord:
    date: str                       # ISO format, YYYY-MM-DD
    household_size: int
    shower_minutes: float = 0.0     # everyone's showers added together
    toilet_flushes: int = 0
    laundry_loads: int = 0
    dishwasher_loads: int = 0
    dish_wash_minutes: float = 0.0  # washing up by hand
    garden_minutes: float = 0.0     # hose / sprinkler running time
    car_washes: int = 0
    drinking_cooking_liters: float = 0.0
    notes: str = ""
    record_id: int = 0
    # Filled in by calculator.apply() - never typed by the user.
    total_liters: float = 0.0
    per_person_liters: float = 0.0
    status: str = ""

    def to_dict(self) -> dict:
        return asdict(self)
