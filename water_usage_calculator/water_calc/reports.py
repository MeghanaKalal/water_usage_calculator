"""Summary maths plus exporting to Markdown, plain text and CSV."""

import csv
from datetime import datetime
from pathlib import Path

from . import calculator, config
from .models import ALL_FIELDS


def summarize(records) -> dict:
    """Roll a list of records up into headline numbers. Returns {} if empty."""
    if not records:
        return {}
    ordered = sorted(records, key=lambda r: (r.date, r.record_id))
    count = len(ordered)
    total = sum(r.total_liters for r in ordered)

    # Category totals across all records.
    categories = {}
    for rec in ordered:
        for name, litres in calculator.breakdown(rec).items():
            categories[name] = categories.get(name, 0.0) + litres
    shares = {k: (v / total * 100 if total else 0.0) for k, v in categories.items()}

    status_counts = {s: 0 for s in calculator.STATUS_ORDER}
    for rec in ordered:
        status_counts[rec.status] = status_counts.get(rec.status, 0) + 1

    # Trend: last 7 entries vs the 7 before them.
    trend = "Not enough data yet (need 8+ entries)"
    if count >= 8:
        recent = ordered[-7:]
        earlier = ordered[-14:-7] or ordered[:-7]
        recent_avg = sum(r.per_person_liters for r in recent) / len(recent)
        earlier_avg = sum(r.per_person_liters for r in earlier) / len(earlier)
        change = recent_avg - earlier_avg
        if abs(change) < 2:
            trend = "Steady - about the same as before"
        elif change > 0:
            trend = f"Rising - up {change:.1f} L/person vs the previous stretch"
        else:
            trend = f"Falling - down {abs(change):.1f} L/person vs the previous stretch"

    highest = max(ordered, key=lambda r: r.total_liters)
    lowest = min(ordered, key=lambda r: r.total_liters)
    flagged = [r for r in ordered if calculator.warnings_for(r)]

    return {
        "count": count,
        "first_date": ordered[0].date,
        "last_date": ordered[-1].date,
        "total_liters": total,
        "avg_daily": total / count,
        "avg_per_person": sum(r.per_person_liters for r in ordered) / count,
        "highest": highest,
        "lowest": lowest,
        "categories": categories,
        "shares": shares,
        "status_counts": status_counts,
        "trend": trend,
        "flagged_count": len(flagged),
    }


def summary_lines(s: dict) -> list:
    """Summary as plain text lines (used on screen, in .txt and in .md)."""
    if not s:
        return ["No records yet - add an entry first."]
    lines = [
        f"Period covered      : {s['first_date']} to {s['last_date']}",
        f"Entries             : {s['count']}",
        f"Total water used    : {s['total_liters']:,.1f} L",
        f"Average per day     : {s['avg_daily']:,.1f} L",
        f"Average per person  : {s['avg_per_person']:,.1f} L/day",
        f"Highest day         : {s['highest'].date} ({s['highest'].total_liters:,.1f} L)",
        f"Lowest day          : {s['lowest'].date} ({s['lowest'].total_liters:,.1f} L)",
        f"Trend               : {s['trend']}",
        f"Entries with alerts : {s['flagged_count']}",
        "",
        "Status breakdown:",
    ]
    for status in calculator.STATUS_ORDER:
        n = s["status_counts"].get(status, 0)
        lines.append(f"  {status:<10} {n:>3} day(s)")
    lines += ["", "Where the water goes:"]
    for name, litres in sorted(s["categories"].items(), key=lambda kv: -kv[1]):
        lines.append(f"  {name:<20} {litres:>10,.1f} L  ({s['shares'][name]:>4.1f}%)")
    return lines


def _stamped_path(kind: str, extension: str) -> Path:
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return config.REPORT_DIR / f"water_{kind}_{stamp}.{extension}"


def export_markdown(records) -> Path:
    s = summarize(records)
    path = _stamped_path("report", "md")
    out = ["# Water Usage Report", "", f"_Generated {datetime.now():%Y-%m-%d %H:%M}_", "",
           "## Summary", "", "```"]
    out += summary_lines(s)
    out += ["```", "", "## Daily records", "",
            "| Date | People | Total (L) | L/person | Status | Notes |",
            "|------|-------:|----------:|---------:|--------|-------|"]
    for r in sorted(records, key=lambda r: (r.date, r.record_id)):
        note = r.notes.replace("|", "/")
        out.append(f"| {r.date} | {r.household_size} | {r.total_liters:,.1f} | "
                   f"{r.per_person_liters:,.1f} | {r.status} | {note} |")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def export_text_log(records) -> Path:
    """Plain-text audit log: the summary, then every record with its alerts."""
    path = _stamped_path("audit", "txt")
    out = ["WATER USAGE AUDIT LOG", f"Generated {datetime.now():%Y-%m-%d %H:%M:%S}", "=" * 60, ""]
    out += summary_lines(summarize(records))
    out += ["", "-" * 60, "RECORD DETAIL", "-" * 60]
    for r in sorted(records, key=lambda r: (r.date, r.record_id)):
        out.append(f"#{r.record_id:<4} {r.date}  {r.total_liters:>8,.1f} L  "
                   f"{r.per_person_liters:>6,.1f} L/person  [{r.status}]  {r.notes}")
        for warning in calculator.warnings_for(r):
            out.append(f"        WARNING: {warning}")
    path.write_text("\n".join(out) + "\n", encoding="utf-8")
    return path


def export_csv(records) -> Path:
    path = _stamped_path("records", "csv")
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=ALL_FIELDS)
        writer.writeheader()
        for r in sorted(records, key=lambda r: (r.date, r.record_id)):
            writer.writerow(r.to_dict())
    return path
