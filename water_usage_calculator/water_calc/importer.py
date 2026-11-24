"""Bulk import from a CSV file, with a row-by-row error log."""

import csv
from datetime import datetime
from pathlib import Path

from . import config
from .storage import next_id
from .validation import record_from_raw

REQUIRED_COLUMNS = ["date", "household_size"]


def import_csv(path, existing_records):
    """Read a CSV and return (new_records, errors, skipped_duplicates).

    Nothing is saved here - the caller decides what to do with the result.
    `errors` is a list of "Row 7: reason" strings.
    """
    path = Path(path).expanduser()
    new_records, errors, duplicates = [], [], 0

    # A duplicate = same date, household size and total as something we already hold.
    seen = {(r.date, r.household_size, r.total_liters) for r in existing_records}
    free_id = next_id(existing_records)

    try:
        handle = path.open("r", newline="", encoding="utf-8-sig")
    except FileNotFoundError:
        return [], [f"File not found: {path}"], 0
    except OSError as problem:
        return [], [f"Couldn't open file: {problem}"], 0

    with handle:
        reader = csv.DictReader(handle)
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
        missing = [c for c in REQUIRED_COLUMNS if c not in headers]
        if missing:
            return [], [f"Header problem: missing column(s) {', '.join(missing)}."], 0

        # Row 1 is the header, so data starts at row 2 (matches what Excel shows).
        for row_number, row in enumerate(reader, start=2):
            clean_row = {(k or "").strip().lower(): v for k, v in row.items()}
            clean_row.pop("record_id", None)  # we hand out our own ids
            try:
                rec = record_from_raw(clean_row)
            except ValueError as problem:
                errors.append(f"Row {row_number}: {problem}")
                continue
            key = (rec.date, rec.household_size, rec.total_liters)
            if key in seen:
                duplicates += 1
                continue
            seen.add(key)
            rec.record_id = free_id
            free_id += 1
            new_records.append(rec)
    return new_records, errors, duplicates


def write_error_log(source_name, errors) -> Path:
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    log = config.REPORT_DIR / f"import_errors_{datetime.now():%Y%m%d_%H%M%S}.log"
    lines = [f"Import errors for {source_name}", f"{len(errors)} problem(s)", ""] + errors
    log.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return log
