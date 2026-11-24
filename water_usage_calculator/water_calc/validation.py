"""Everything about checking what the user (or a CSV file) gives us.

Two layers live here:
  1. clean_* functions - pure checks that raise ValueError with a friendly message.
  2. ask_* functions   - keep prompting at the terminal until the answer passes.

The importer reuses the same clean_* functions, so typed input and imported
rows are held to exactly the same rules.
"""

import math
import re
from dataclasses import dataclass
from datetime import date, datetime

from . import calculator
from .models import UsageRecord


class CancelEntry(Exception):
    """Raised when the user types 'q' to back out of a prompt."""


@dataclass(frozen=True)
class Spec:
    kind: str      # "int" or "float"
    low: float
    high: float
    label: str     # what we call it when talking to the user


SPECS = {
    "household_size":          Spec("int",   1,  20,  "Household size (people)"),
    "shower_minutes":          Spec("float", 0, 300,  "Total shower minutes (everyone combined)"),
    "toilet_flushes":          Spec("int",   0, 100,  "Toilet flushes"),
    "laundry_loads":           Spec("int",   0,  10,  "Laundry loads"),
    "dishwasher_loads":        Spec("int",   0,  10,  "Dishwasher loads"),
    "dish_wash_minutes":       Spec("float", 0, 120,  "Minutes washing dishes by hand"),
    "garden_minutes":          Spec("float", 0, 480,  "Minutes of garden watering"),
    "car_washes":              Spec("int",   0,   5,  "Car washes at home"),
    "drinking_cooking_liters": Spec("float", 0, 100,  "Drinking & cooking water (litres)"),
}

EARLIEST_DATE = date(2000, 1, 1)
MAX_NOTE_LENGTH = 120


# --------------------------------------------------------------------------
# Pure cleaners
# --------------------------------------------------------------------------
def clean_number(name: str, raw) -> float:
    spec = SPECS[name]
    text = str(raw).strip()
    if not text:
        raise ValueError(f"{spec.label} can't be blank.")
    try:
        number = float(text)
    except ValueError:
        raise ValueError(f"'{text}' isn't a number. Please type digits only.") from None
    if not math.isfinite(number):
        raise ValueError("That isn't a real number.")
    if spec.kind == "int":
        if number != int(number):
            raise ValueError(f"{spec.label} must be a whole number.")
        number = int(number)
    else:
        number = round(number, 1)
    if not spec.low <= number <= spec.high:
        raise ValueError(f"{spec.label} must be between {spec.low:g} and {spec.high:g}.")
    return number


def clean_date(raw) -> str:
    text = str(raw).strip()
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValueError("Dates look like 2026-11-24 (YYYY-MM-DD).")
    try:
        parsed = datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        raise ValueError(f"'{text}' isn't a real calendar date.") from None
    if parsed > date.today():
        raise ValueError("That date is in the future - we can only log what's already happened.")
    if parsed < EARLIEST_DATE:
        raise ValueError("That date is too far back (earliest allowed is 2000-01-01).")
    return text


def clean_notes(raw) -> str:
    text = re.sub(r"[\x00-\x1f\x7f]", " ", str(raw or "")).strip()
    return text[:MAX_NOTE_LENGTH]


def record_from_raw(raw: dict) -> UsageRecord:
    """Build a fully validated, fully calculated record from a plain dict.

    Date and household size are required. Any other missing/blank amount is
    treated as zero, which keeps older or hand-edited files usable.
    """
    values = {"date": clean_date(raw.get("date", ""))}
    for name in SPECS:
        value = raw.get(name)
        blank = value is None or str(value).strip() == ""
        if blank and name != "household_size":
            value = 0
        values[name] = clean_number(name, value)
    values["notes"] = clean_notes(raw.get("notes", ""))

    rec = UsageRecord(**values)
    try:
        rec.record_id = int(raw.get("record_id") or 0)
    except (TypeError, ValueError):
        rec.record_id = 0
    return calculator.apply(rec)


# --------------------------------------------------------------------------
# Interactive prompts
# --------------------------------------------------------------------------
def _read(prompt: str) -> str:
    answer = input(prompt).strip()
    if answer.lower() in ("q", "quit", "cancel"):
        raise CancelEntry
    return answer


def ask_number(name: str, default=None):
    spec = SPECS[name]
    shown = f" [{default}]" if default is not None else ""
    while True:
        answer = _read(f"  {spec.label} ({spec.low:g}-{spec.high:g}){shown}: ")
        if answer == "" and default is not None:
            return default
        try:
            return clean_number(name, answer)
        except ValueError as problem:
            print(f"    ! {problem}")


def ask_date(default: str = None) -> str:
    shown = f" [{default}]" if default else ""
    while True:
        answer = _read(f"  Date YYYY-MM-DD{shown}: ")
        if answer == "" and default:
            return default
        try:
            return clean_date(answer)
        except ValueError as problem:
            print(f"    ! {problem}")


def ask_text(prompt: str, allow_blank: bool = True) -> str:
    while True:
        answer = _read(f"  {prompt}: ")
        if answer or allow_blank:
            return clean_notes(answer)
        print("    ! Please type something.")


def ask_yes_no(prompt: str, default: bool = False) -> bool:
    hint = "Y/n" if default else "y/N"
    while True:
        answer = input(f"  {prompt} ({hint}): ").strip().lower()
        if answer == "":
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("    ! Please answer y or n.")


def ask_menu_choice(valid: list) -> str:
    while True:
        answer = input("\n  Choose an option: ").strip()
        if answer in valid:
            return answer
        print(f"    ! '{answer}' isn't on the menu. Try one of: {', '.join(valid)}")
