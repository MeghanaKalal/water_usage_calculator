"""Saving and loading records as JSON, without ever crashing on a bad file."""

import json
import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

from . import config
from .validation import record_from_raw


def load_records(path: Path = None):
    """Return (records, messages).

    * Missing file  -> start fresh and create it.
    * Corrupted file -> keep a .corrupt backup, start fresh.
    * A few bad rows -> skip them, tell the user how many.
    """
    path = Path(path or config.DATA_FILE)
    messages = []

    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        save_records([], path)
        return [], ["No saved data found - starting with a clean slate."]
    except OSError as problem:
        return [], [f"Couldn't read {path.name}: {problem}"]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup = path.with_name(f"{path.stem}.corrupt-{stamp}{path.suffix}")
        try:
            shutil.copy2(path, backup)
            messages.append(f"Your data file was unreadable. A copy was kept as {backup.name}.")
        except OSError:
            messages.append("Your data file was unreadable and a backup couldn't be made.")
        save_records([], path)
        messages.append("Starting with a clean slate.")
        return [], messages

    # Accept both {"records": [...]} and a bare list.
    items = payload.get("records") if isinstance(payload, dict) else payload
    if not isinstance(items, list):
        messages.append("Data file had an unexpected layout - starting fresh.")
        return [], messages

    records, skipped = [], 0
    for item in items:
        try:
            records.append(record_from_raw(item))
        except (ValueError, AttributeError, TypeError):
            skipped += 1
    if skipped:
        messages.append(f"Skipped {skipped} stored row(s) that failed validation.")

    # Make sure every record has a unique id.
    seen = set()
    next_free = max([r.record_id for r in records] + [0]) + 1
    for rec in records:
        if rec.record_id <= 0 or rec.record_id in seen:
            rec.record_id = next_free
            next_free += 1
        seen.add(rec.record_id)
    return records, messages


def save_records(records, path: Path = None) -> None:
    """Write atomically: temp file first, then swap, so a crash can't half-write."""
    path = Path(path or config.DATA_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": config.SCHEMA_VERSION,
        "saved_at": datetime.now().isoformat(timespec="seconds"),
        "records": [r.to_dict() for r in records],
    }
    fd, temp_name = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)
        os.replace(temp_name, path)
    except BaseException:
        if os.path.exists(temp_name):
            os.remove(temp_name)
        raise


def next_id(records) -> int:
    return max((r.record_id for r in records), default=0) + 1
