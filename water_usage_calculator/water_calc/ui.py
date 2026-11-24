"""The terminal side of things: banner, menu, tables and the main loop."""

import os
import sys

from . import calculator, config, importer, plots, reports, storage
from .models import UsageRecord
from .search import filter_records
from .validation import (CancelEntry, SPECS, ask_date, ask_menu_choice, ask_number,
                         ask_text, ask_yes_no, clean_date)

# --- colours (switched off automatically when output isn't a real terminal) ---
os.system("")  # quietly enables ANSI colours on Windows 10+
USE_COLOR = sys.stdout.isatty() and "NO_COLOR" not in os.environ


def paint(text, code):
    return f"\033[{code}m{text}\033[0m" if USE_COLOR else str(text)


def blue(t): return paint(t, "36;1")
def green(t): return paint(t, "32")
def yellow(t): return paint(t, "33")
def red(t): return paint(t, "31;1")
def dim(t): return paint(t, "2")


STATUS_PAINT = {"Efficient": green, "Moderate": yellow, "High": yellow, "Critical": red}

BANNER = r"""
  __        __   _                _   _
  \ \      / /_ _| |_ ___ _ __   | | | |___  __ _  __ _  ___
   \ \ /\ / / _` | __/ _ \ '__|  | | | / __|/ _` |/ _` |/ _ \
    \ V  V / (_| | ||  __/ |     | |_| \__ \ (_| | (_| |  __/
     \_/\_/ \__,_|\__\___|_|      \___/|___/\__,_|\__, |\___|
                                                   |___/
"""

MENU = [
    ("1", "Add a daily entry"),
    ("2", "View all records"),
    ("3", "Search / filter records"),
    ("4", "Summary report"),
    ("5", "Create charts (PNG)"),
    ("6", "Export report (Markdown / text / CSV)"),
    ("7", "Import records from CSV"),
    ("8", "Delete a record"),
    ("9", "Load the sample dataset"),
    ("0", "Exit"),
]


def heading(title):
    print("\n" + blue(f"== {title} " + "=" * max(0, 52 - len(title))))


def show_banner():
    print(blue(BANNER))
    print("  Estimate your household's daily water use from simple activities.")
    print(dim("  Tip: type 'q' at any prompt to cancel what you're doing.\n"))


def show_menu():
    heading("Main menu")
    for key, label in MENU:
        print(f"  [{key}] {label}")


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def print_table(rows):
    header = f"{'ID':>4}  {'Date':<10}  {'People':>6}  {'Total L':>9}  {'L/person':>9}  {'Status':<9}  Notes"
    print(dim(header))
    print(dim("-" * 78))
    for r in rows:
        status = STATUS_PAINT.get(r.status, str)(f"{r.status:<9}")
        note = r.notes if len(r.notes) <= 24 else r.notes[:21] + "..."
        print(f"{r.record_id:>4}  {r.date:<10}  {r.household_size:>6}  "
              f"{r.total_liters:>9,.1f}  {r.per_person_liters:>9,.1f}  {status}  {note}")


def show_paged(rows):
    """Print rows a page at a time so long lists stay readable."""
    if not rows:
        print("  Nothing to show.")
        return
    size = config.PAGE_SIZE
    pages = (len(rows) + size - 1) // size
    for page in range(pages):
        chunk = rows[page * size:(page + 1) * size]
        print()
        print_table(chunk)
        print(dim(f"\n  Page {page + 1} of {pages}  ({len(rows)} records)"))
        if page < pages - 1:
            if input("  Press Enter for the next page, or q to stop: ").strip().lower() == "q":
                break


def show_warnings(rec):
    for message in calculator.warnings_for(rec):
        print(red("  ⚠ ") + yellow(message))


# --------------------------------------------------------------------------
# Menu actions
# --------------------------------------------------------------------------
def add_entry(records):
    heading("Add a daily entry")
    print(dim("  Press Enter to accept the value in [brackets].\n"))
    try:
        from datetime import date
        values = {"date": ask_date(default=date.today().isoformat())}
        last_size = records[-1].household_size if records else None
        values["household_size"] = ask_number("household_size", default=last_size)
        for name in list(SPECS)[1:]:
            values[name] = ask_number(name, default=0)
        values["notes"] = ask_text("Notes (optional)")
    except CancelEntry:
        print("  Okay, entry cancelled - nothing was saved.")
        return

    from .validation import record_from_raw
    rec = record_from_raw(values)
    rec.record_id = storage.next_id(records)

    heading("Here's what we worked out")
    for name, litres in calculator.breakdown(rec).items():
        if litres:
            print(f"  {name:<20} {litres:>9,.1f} L")
    print(f"  {'-' * 31}")
    print(f"  {'Total':<20} {rec.total_liters:>9,.1f} L")
    print(f"  {'Per person':<20} {rec.per_person_liters:>9,.1f} L  -> "
          f"{STATUS_PAINT[rec.status](rec.status)}")
    show_warnings(rec)

    if ask_yes_no("Save this entry?", default=True):
        records.append(rec)
        storage.save_records(records)
        print(green(f"  Saved as record #{rec.record_id}."))
    else:
        print("  Discarded.")


def view_all(records):
    heading("All records")
    show_paged(sorted(records, key=lambda r: (r.date, r.record_id)))


def search_menu(records):
    heading("Search / filter")
    if not records:
        print("  No records to search yet.")
        return
    print(dim("  Leave any filter blank to skip it.\n"))
    try:
        keyword = input("  Keyword (date text or notes): ").strip() or None
        status = None
        raw_status = input("  Status (Efficient / Moderate / High / Critical): ").strip()
        if raw_status:
            match = [s for s in calculator.STATUS_ORDER if s.lower() == raw_status.lower()]
            if not match:
                print(red("  ! That isn't a status, so the filter was ignored."))
            else:
                status = match[0]
        start = _optional_date("  From date (YYYY-MM-DD): ")
        end = _optional_date("  To date   (YYYY-MM-DD): ")
        min_pp = _optional_float("  Minimum litres per person: ")
    except CancelEntry:
        return
    results = filter_records(records, keyword, status, start, end, min_pp)
    print(f"\n  Found {len(results)} matching record(s).")
    show_paged(results)


def _optional_date(prompt):
    while True:
        raw = input(prompt).strip()
        if raw.lower() == "q":
            raise CancelEntry
        if not raw:
            return None
        try:
            return clean_date(raw)
        except ValueError as problem:
            print(f"    ! {problem}")


def _optional_float(prompt):
    while True:
        raw = input(prompt).strip()
        if raw.lower() == "q":
            raise CancelEntry
        if not raw:
            return None
        try:
            value = float(raw)
            if value < 0:
                raise ValueError
            return value
        except ValueError:
            print("    ! Please type a positive number, or leave it blank.")


def show_summary(records):
    heading("Summary report")
    for line in reports.summary_lines(reports.summarize(records)):
        print("  " + line)
    flagged = [r for r in records if calculator.warnings_for(r)]
    if flagged:
        print("\n" + yellow("  Entries needing a look:"))
        for rec in sorted(flagged, key=lambda r: r.date)[:10]:
            print(f"   #{rec.record_id} {rec.date}")
            for message in calculator.warnings_for(rec):
                print(red("     ⚠ ") + message)
        if len(flagged) > 10:
            print(dim(f"   ...and {len(flagged) - 10} more (see the text audit log export)."))


def make_charts(records):
    heading("Charts")
    if not records:
        print("  Add some records first - there's nothing to plot yet.")
        return
    paths = plots.make_all(records)
    if paths is None:
        print(yellow("  matplotlib isn't installed, so charts are unavailable."))
        print("  Install it with:  pip install matplotlib")
        return
    print(green("  Charts saved:"))
    for path in paths:
        print(f"   - {path}")


def export_menu(records):
    heading("Export report")
    if not records:
        print("  Nothing to export yet.")
        return
    print("  [1] Markdown summary\n  [2] Plain-text audit log\n  [3] CSV of all records\n  [4] All three")
    choice = ask_menu_choice(["1", "2", "3", "4"])
    made = []
    if choice in ("1", "4"):
        made.append(reports.export_markdown(records))
    if choice in ("2", "4"):
        made.append(reports.export_text_log(records))
    if choice in ("3", "4"):
        made.append(reports.export_csv(records))
    print(green("  Exported:"))
    for path in made:
        print(f"   - {path}")


def import_menu(records, path_text=None):
    heading("Import from CSV")
    if path_text is None:
        print(dim("  Needs at least 'date' and 'household_size' columns."))
        path_text = input("  Path to CSV file (q to cancel): ").strip().strip('"')
        if path_text.lower() in ("", "q"):
            return
    new, errors, dupes = importer.import_csv(path_text, records)
    if new:
        records.extend(new)
        storage.save_records(records)
    print(green(f"  Imported {len(new)} record(s)."))
    if dupes:
        print(f"  Skipped {dupes} duplicate row(s).")
    if errors:
        print(yellow(f"  {len(errors)} problem(s) found:"))
        for line in errors[:8]:
            print(f"   - {line}")
        log = importer.write_error_log(path_text, errors)
        print(f"  Full list saved to {log}")


def delete_record(records):
    heading("Delete a record")
    if not records:
        print("  No records to delete.")
        return
    raw = input("  Record ID to delete (q to cancel): ").strip()
    if not raw.isdigit():
        if raw.lower() != "q":
            print(red("  ! That isn't a valid ID."))
        return
    target = next((r for r in records if r.record_id == int(raw)), None)
    if target is None:
        print(red(f"  ! No record with ID {raw}."))
        return
    print_table([target])
    if ask_yes_no("Really delete this record?"):
        records.remove(target)
        storage.save_records(records)
        print(green("  Deleted."))


def load_sample(records):
    heading("Load sample dataset")
    if not config.SAMPLE_CSV.exists():
        print(red("  Sample file data/sample_data.csv is missing."))
        return
    import_menu(records, path_text=str(config.SAMPLE_CSV))


# --------------------------------------------------------------------------
# Main loop
# --------------------------------------------------------------------------
def run():
    show_banner()
    records, messages = storage.load_records()
    for message in messages:
        print(yellow("  " + message))
    print(f"  {len(records)} record(s) loaded.")

    actions = {
        "1": add_entry, "2": view_all, "3": search_menu, "4": show_summary,
        "5": make_charts, "6": export_menu, "7": import_menu,
        "8": delete_record, "9": load_sample,
    }
    valid = [key for key, _ in MENU]
    try:
        while True:
            show_menu()
            choice = ask_menu_choice(valid)
            if choice == "0":
                break
            try:
                actions[choice](records)
            except CancelEntry:
                print("  Cancelled.")
            input(dim("\n  Press Enter to return to the menu..."))
    except (KeyboardInterrupt, EOFError):
        print()
    print(green("\n  Thanks for saving water today! Goodbye.\n"))
