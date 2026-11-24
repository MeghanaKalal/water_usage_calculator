"""Charts with matplotlib. If matplotlib isn't installed we say so politely."""

from datetime import datetime

from . import calculator, config
from .reports import summarize

try:
    import matplotlib
    matplotlib.use("Agg")  # draw to files; no window needed
    import matplotlib.pyplot as plt
    HAVE_MPL = True
except ImportError:  # pragma: no cover - depends on the machine
    HAVE_MPL = False

STATUS_COLORS = {"Efficient": "#2a9d8f", "Moderate": "#e9c46a", "High": "#f4a261", "Critical": "#e63946"}


def _save(fig, name: str):
    config.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = config.REPORT_DIR / f"water_{name}_{stamp}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    return path


def trend_chart(records):
    """Per-person litres each day, a 7-day average, and the status limits."""
    ordered = sorted(records, key=lambda r: (r.date, r.record_id))
    dates = [datetime.strptime(r.date, "%Y-%m-%d") for r in ordered]
    values = [r.per_person_liters for r in ordered]

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(dates, values, marker="o", color="#264653", linewidth=1.5, label="Per person")
    if len(values) >= 3:
        rolling = []
        for i in range(len(values)):
            window = values[max(0, i - 6): i + 1]
            rolling.append(sum(window) / len(window))
        ax.plot(dates, rolling, color="#e76f51", linestyle="--", linewidth=2, label="7-day average")
    for limit, label in calculator.STATUS_LEVELS:
        ax.axhline(limit, color="grey", linestyle=":", linewidth=1)
        ax.text(dates[-1], limit + 4, f"{label} limit ({limit} L)", fontsize=8, color="dimgrey",
                ha="right", bbox=dict(facecolor="white", edgecolor="none", alpha=0.8, pad=1))
    ax.set_title("Daily water use per person")
    ax.set_ylabel("Litres per person")
    ax.set_xlabel("Date")
    ax.grid(alpha=0.25)
    ax.legend()
    fig.autofmt_xdate()
    return _save(fig, "trend")


def breakdown_chart(records):
    s = summarize(records)
    items = sorted(s["categories"].items(), key=lambda kv: kv[1])
    names = [k for k, _ in items]
    litres = [v for _, v in items]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.barh(names, litres, color="#2a9d8f")
    for bar, name, value in zip(bars, names, litres):
        share = s["shares"][name]
        ax.text(bar.get_width(), bar.get_y() + bar.get_height() / 2,
                f"  {value:,.0f} L ({share:.0f}%)", va="center", fontsize=9)
    ax.set_title("Where the water goes")
    ax.set_xlabel("Total litres")
    ax.set_xlim(0, max(litres) * 1.25 if litres else 1)
    return _save(fig, "breakdown")


def status_chart(records):
    s = summarize(records)
    names = calculator.STATUS_ORDER
    counts = [s["status_counts"].get(n, 0) for n in names]

    fig, ax = plt.subplots(figsize=(7, 5))
    ax.bar(names, counts, color=[STATUS_COLORS[n] for n in names])
    for i, c in enumerate(counts):
        ax.text(i, c + 0.1, str(c), ha="center")
    ax.set_title("How many days fell in each status")
    ax.set_ylabel("Days")
    return _save(fig, "status")


def make_all(records):
    """Return a list of saved image paths, or None if matplotlib is missing."""
    if not HAVE_MPL:
        return None
    return [trend_chart(records), breakdown_chart(records), status_chart(records)]
