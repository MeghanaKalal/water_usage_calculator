# Water Usage Calculator

A beginner-friendly Python command-line app that estimates how much water a household
uses in a day from simple activities (showers, flushes, laundry, garden, and so on),
saves every entry to disk, and turns the history into summaries, warnings and charts.

Built for the **DataSpark Challenge - Project #44 (Environment & Sustainability)**.

## Quick start

```bash
# 1. (optional) create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. (optional) install matplotlib for charts - everything else is standard library
pip install -r requirements.txt

# 3. run it
python main.py
```

Needs Python 3.10 or newer. On first launch choose **[9] Load the sample dataset** to
get 38 realistic entries to play with.

## Feature checklist

| Brief requirement | Where it lives |
|---|---|
| Interactive menu-driven terminal UI (ANSI colours, banner, pagination) | `water_calc/ui.py` |
| Defensive input validation (types, ranges, dates, blanks, `q` to cancel) | `water_calc/validation.py` |
| Calculation engine + status levels | `water_calc/calculator.py` |
| JSON persistence, atomic saves, corrupt-file recovery | `water_calc/storage.py` |
| Keyword / status / date-range / usage filters | `water_calc/search.py` |
| Summary (totals, averages, trend, breakdown, status counts) | `water_calc/reports.py` |
| Matplotlib charts (trend, breakdown, status) | `water_calc/plots.py` |
| **Stretch:** Markdown, text audit log and CSV export | `water_calc/reports.py` |
| **Stretch:** Threshold warnings (critical, anomalous, zero use...) | `calculator.warnings_for` |
| **Stretch:** Bulk CSV import with row-by-row error log | `water_calc/importer.py` |

## How the estimate works

Each daily entry is converted to litres with these rates (edit `RATES` in `calculator.py`):

| Activity | Litres |
|---|---|
| Shower | 9 per minute |
| Toilet flush | 6 each |
| Laundry load | 50 each |
| Dishwasher cycle | 15 each |
| Hand dishwashing | 8 per minute |
| Garden hose | 15 per minute |
| Car wash at home | 150 each |
| Drinking & cooking | as entered |

Total litres divided by household size gives **litres per person**, which sets the status:

| Per person per day | Status |
|---|---|
| up to 100 L | Efficient |
| 101 - 150 L | Moderate |
| 151 - 200 L | High |
| over 200 L | Critical |

Warnings also appear for zero usage, more than 300 L/person (probably a typo), very long
showers, too many flushes, and garden watering over two hours.

## Project layout

```
water_usage_calculator/
├── main.py                  # entry point
├── requirements.txt
├── water_calc/              # the application package
│   ├── config.py            # paths and settings
│   ├── models.py            # UsageRecord dataclass
│   ├── calculator.py        # litres, status, warnings
│   ├── validation.py        # cleaners + prompt loops
│   ├── storage.py           # JSON load/save
│   ├── search.py            # filtering
│   ├── reports.py           # summary + exports
│   ├── plots.py             # matplotlib charts
│   ├── importer.py          # CSV bulk import
│   └── ui.py                # menu and tables
├── data/
│   ├── sample_data.csv      # 38 entries (normal, boundary and edge cases)
│   ├── sample_data.json     # same data in the app's stored format
│   └── bad_rows_demo.csv    # deliberately broken rows for the import demo
├── scripts/generate_sample_data.py
├── tests/test_water_calc.py
└── reports/                 # exports and charts land here
```

Your own entries are saved in `data/records.json` (created on first run).

## Demo script (about 5 minutes)

1. Launch `python main.py` - point out the banner and menu.
2. **[9]** load the sample data, then **[2]** to browse the paginated table.
3. **[1]** add an entry. Type `abc` for shower minutes, then `999`, then a valid number
   to show validation. Also try a future date.
4. **[4]** summary - highlight the trend, "where the water goes" and the alert list.
5. **[3]** search for `guests`, or filter by status `Critical`.
6. **[7]** import `data/bad_rows_demo.csv` to show the row-by-row error report.
7. **[5]** and **[6]** create the charts and export the Markdown/text/CSV reports.
8. Exit with **[0]**, relaunch, and show that every record is still there.

## Tests

```bash
python -m unittest discover -s tests -v
```

Covers the calculator, validation rules, search, storage recovery (missing, corrupt and
partly-bad files), CSV import and the summary maths.

## Customising

* Different household? Change `RATES` or `STATUS_LEVELS` in `calculator.py`.
* Different input limits? Edit `SPECS` in `validation.py` - prompts, imports and stored
  data all pick up the change.
* Store data elsewhere: set the `WATER_DATA_FILE` environment variable to a JSON path.
* Turn off colours: set `NO_COLOR=1`.
