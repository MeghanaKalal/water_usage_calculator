"""Paths and a few settings in one place so nothing is hard-coded elsewhere."""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
REPORT_DIR = BASE_DIR / "reports"

# Handy for demos/tests: set WATER_DATA_FILE to use a different store.
DATA_FILE = Path(os.environ.get("WATER_DATA_FILE", DATA_DIR / "records.json"))
SAMPLE_CSV = DATA_DIR / "sample_data.csv"

SCHEMA_VERSION = 1
PAGE_SIZE = 10  # rows shown per page in tables
