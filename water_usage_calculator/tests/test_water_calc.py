"""Run with:  python -m unittest discover -s tests -v"""

import json
import os
import tempfile
import unittest
from pathlib import Path

from water_calc import calculator, importer, reports, storage
from water_calc.search import filter_records
from water_calc.validation import clean_date, clean_number, record_from_raw


def make(**overrides):
    raw = {"date": "2026-11-01", "household_size": 4, "shower_minutes": 30,
           "toilet_flushes": 20, "laundry_loads": 1, "dishwasher_loads": 1,
           "dish_wash_minutes": 5, "garden_minutes": 0, "car_washes": 0,
           "drinking_cooking_liters": 16, "notes": "test"}
    raw.update(overrides)
    return record_from_raw(raw)


class CalculatorTests(unittest.TestCase):
    def test_total_is_sum_of_activities(self):
        # 30*9 + 20*6 + 50 + 15 + 5*8 + 16 = 270+120+50+15+40+16 = 511
        rec = make()
        self.assertEqual(rec.total_liters, 511.0)
        self.assertEqual(rec.per_person_liters, 127.8)
        self.assertEqual(rec.status, "Moderate")

    def test_status_boundaries(self):
        self.assertEqual(calculator.classify(100), "Efficient")
        self.assertEqual(calculator.classify(100.1), "Moderate")
        self.assertEqual(calculator.classify(200), "High")
        self.assertEqual(calculator.classify(200.1), "Critical")

    def test_zero_usage_warns(self):
        rec = make(shower_minutes=0, toilet_flushes=0, laundry_loads=0, dishwasher_loads=0,
                   dish_wash_minutes=0, drinking_cooking_liters=0)
        self.assertTrue(any("No water use" in w for w in calculator.warnings_for(rec)))


class ValidationTests(unittest.TestCase):
    def test_rejects_text_blank_negative_and_huge(self):
        for bad in ["abc", "", "-1", "9999", "nan", "inf"]:
            with self.assertRaises(ValueError):
                clean_number("shower_minutes", bad)

    def test_whole_number_rule(self):
        with self.assertRaises(ValueError):
            clean_number("toilet_flushes", "2.5")
        self.assertEqual(clean_number("toilet_flushes", "3.0"), 3)

    def test_dates(self):
        self.assertEqual(clean_date("2026-02-28"), "2026-02-28")
        for bad in ["2026-02-30", "28/02/2026", "2999-01-01", "1999-12-31", ""]:
            with self.assertRaises(ValueError):
                clean_date(bad)


class SearchTests(unittest.TestCase):
    def setUp(self):
        self.records = [make(date="2026-11-01", notes="Guests"),
                        make(date="2026-11-05", notes="Quiet", garden_minutes=10),
                        make(date="2026-11-09", notes="guests again")]

    def test_keyword_is_case_insensitive(self):
        self.assertEqual(len(filter_records(self.records, keyword="GUESTS")), 2)

    def test_date_range_and_status(self):
        self.assertEqual(len(filter_records(self.records, start="2026-11-02", end="2026-11-08")), 1)
        self.assertEqual(len(filter_records(self.records, status="High")), 1)


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "records.json"

    def tearDown(self):
        self.tmp.cleanup()

    def test_missing_file_is_created(self):
        records, messages = storage.load_records(self.path)
        self.assertEqual(records, [])
        self.assertTrue(self.path.exists())

    def test_round_trip(self):
        rec = make()
        rec.record_id = 1
        storage.save_records([rec], self.path)
        loaded, _ = storage.load_records(self.path)
        self.assertEqual(loaded[0].total_liters, rec.total_liters)

    def test_corrupt_file_is_backed_up(self):
        self.path.write_text("{ this is not json", encoding="utf-8")
        records, messages = storage.load_records(self.path)
        self.assertEqual(records, [])
        self.assertEqual(len(list(Path(self.tmp.name).glob("*.corrupt-*"))), 1)

    def test_bad_rows_are_skipped_not_fatal(self):
        good = make().to_dict()
        bad = dict(good, household_size=-3)
        self.path.write_text(json.dumps({"records": [good, bad]}), encoding="utf-8")
        records, messages = storage.load_records(self.path)
        self.assertEqual(len(records), 1)
        self.assertTrue(any("Skipped 1" in m for m in messages))


class ImporterTests(unittest.TestCase):
    def test_bad_rows_reported_with_row_numbers(self):
        demo = Path(__file__).resolve().parent.parent / "data" / "bad_rows_demo.csv"
        new, errors, dupes = importer.import_csv(demo, [])
        self.assertEqual(len(new), 2)
        self.assertEqual(len(errors), 6)
        self.assertTrue(errors[0].startswith("Row 3"))

    def test_missing_file_and_missing_header(self):
        self.assertTrue(importer.import_csv("nope.csv", [])[1])
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as f:
            f.write("foo,bar\n1,2\n")
        try:
            self.assertIn("missing column", importer.import_csv(f.name, [])[1][0])
        finally:
            os.remove(f.name)

    def test_duplicates_skipped(self):
        sample = Path(__file__).resolve().parent.parent / "data" / "sample_data.csv"
        first, _, _ = importer.import_csv(sample, [])
        again, _, dupes = importer.import_csv(sample, first)
        self.assertEqual(again, [])
        self.assertEqual(dupes, len(first))


class ReportTests(unittest.TestCase):
    def test_summary_numbers(self):
        s = reports.summarize([make(date="2026-11-01"), make(date="2026-11-02")])
        self.assertEqual(s["count"], 2)
        self.assertEqual(s["total_liters"], 1022.0)
        self.assertEqual(reports.summarize([]), {})


if __name__ == "__main__":
    unittest.main()
