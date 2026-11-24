"""The 'brain': turns daily activities into litres, and litres into a verdict.

The rates below are ballpark figures for a typical home. They're easy to tweak
in one place if you want to model a low-flow shower head or an old toilet.
"""

from .models import UsageRecord

# Litres used per unit of each activity.
RATES = {
    "shower": 9.0,       # per minute (standard shower head)
    "toilet": 6.0,       # per flush
    "laundry": 50.0,     # per washing-machine load
    "dishwasher": 15.0,  # per dishwasher cycle
    "dish_hand": 8.0,    # per minute of washing up with the tap running
    "garden": 15.0,      # per minute of hose use
    "car_wash": 150.0,   # per car wash at home
}

# Per-person daily litres -> label. Roughly in line with WHO guidance (~100 L/day
# covers basic needs) and common urban averages.
STATUS_LEVELS = [
    (100, "Efficient"),
    (150, "Moderate"),
    (200, "High"),
]
CRITICAL = "Critical"
STATUS_ORDER = ["Efficient", "Moderate", "High", "Critical"]

ANOMALY_PER_PERSON = 300  # beyond this, double-check the entry


def breakdown(rec: UsageRecord) -> dict:
    """Litres per category for one record."""
    return {
        "Showers": rec.shower_minutes * RATES["shower"],
        "Toilet": rec.toilet_flushes * RATES["toilet"],
        "Laundry": rec.laundry_loads * RATES["laundry"],
        "Dishwasher": rec.dishwasher_loads * RATES["dishwasher"],
        "Hand dishwashing": rec.dish_wash_minutes * RATES["dish_hand"],
        "Garden": rec.garden_minutes * RATES["garden"],
        "Car washing": rec.car_washes * RATES["car_wash"],
        "Drinking & cooking": rec.drinking_cooking_liters,
    }


def classify(per_person: float) -> str:
    for limit, label in STATUS_LEVELS:
        if per_person <= limit:
            return label
    return CRITICAL


def apply(rec: UsageRecord) -> UsageRecord:
    """Fill in totals and status on a record (modifies and returns it)."""
    total = sum(breakdown(rec).values())
    rec.total_liters = round(total, 1)
    rec.per_person_liters = round(total / rec.household_size, 1)
    rec.status = classify(rec.per_person_liters)
    return rec


def warnings_for(rec: UsageRecord) -> list:
    """Plain-English heads-ups about a record. Empty list = nothing odd."""
    notes = []
    size = rec.household_size

    if rec.total_liters == 0:
        notes.append("No water use recorded at all - is that right?")
    if rec.per_person_liters > ANOMALY_PER_PERSON:
        notes.append(f"{rec.per_person_liters:.0f} L per person is unusually high - please double-check.")
    elif rec.status == CRITICAL:
        notes.append(f"{rec.per_person_liters:.0f} L per person is over the 200 L critical limit.")
    if rec.shower_minutes / size > 30:
        notes.append("Over 30 shower minutes per person - that's a long shower!")
    if rec.toilet_flushes / size > 15:
        notes.append("More than 15 flushes per person looks like a leak or a typo.")
    if rec.garden_minutes > 120:
        notes.append("Garden watering ran over 2 hours.")
    return notes
