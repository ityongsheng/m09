import csv
import json
import tempfile
import unittest
from pathlib import Path

from pipeline.etl.clean_dataset import load_rows, run


class CleanDatasetTests(unittest.TestCase):
    def write_source(self, directory: Path, rows: list[list[str]]) -> Path:
        path = directory / "input.csv"
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Fruit", "Temp", "Humid (%)", "Light (Fux)", "CO2 (pmm)", "Class"])
            writer.writerows(rows)
        return path

    def test_real_dataset_can_be_loaded(self):
        rows = load_rows(Path("data/raw/Dataset.csv"))
        self.assertEqual(len(rows), 10995)
        self.assertEqual(rows[0]["class"], "Good")

    def test_cleaning_maps_labels_and_reports_invalid_rows(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = self.write_source(root, [
                ["Orange", "22", "95", "7.2", "361", "Good"],
                ["Banana", "25", "89", "20", "388", "Bad"],
                ["", "25", "90", "20", "400", "Good"],
                ["Apple", "bad", "90", "20", "400", "Good"],
                ["Apple", "25", "101", "20", "400", "Good"],
                ["Apple", "25", "90", "20", "400", "Unknown"],
            ])
            output = root / "out.csv"
            report = root / "report.json"
            schema = root / "schema.json"
            result = run(source, output, report, schema)
            self.assertEqual(result["stats"]["input_rows"], 6)
            self.assertEqual(result["stats"]["output_rows"], 2)
            self.assertEqual(result["stats"]["dropped_missing"], 1)
            self.assertEqual(result["stats"]["dropped_invalid_numeric"], 1)
            self.assertEqual(result["stats"]["dropped_out_of_range"], 1)
            self.assertEqual(result["stats"]["dropped_invalid_label"], 1)
            with output.open(encoding="utf-8", newline="") as f:
                rows = list(csv.DictReader(f))
            self.assertEqual(rows[0]["label"], "0")
            self.assertEqual(rows[1]["label"], "1")
            self.assertEqual(json.loads(schema.read_text())["has_timestamp"], False)


if __name__ == "__main__":
    unittest.main()
