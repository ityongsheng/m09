#!/usr/bin/env python3
"""Clean and validate the Mendeley cold-storage sensor records."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path
from typing import Iterable

CANONICAL_COLUMNS = ["fruit", "temp", "humid", "light", "co2", "label", "label_name"]
REQUIRED_SOURCE = {
    "fruit": "fruit",
    "temp": "temp",
    "humid": "humid (%)",
    "light": "light (fux)",
    "co2": "co2 (pmm)",
    "class": "class",
}
NUMERIC_RANGES = {
    "temp": (-50.0, 80.0),
    "humid": (0.0, 100.0),
    "light": (0.0, 1_000_000.0),
    "co2": (0.0, 100_000.0),
}
LABELS = {"good": (0, "Good"), "bad": (1, "Bad")}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalise_header(value: str) -> str:
    return " ".join(value.strip().lower().split())


def load_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError("CSV 缺少表头")
        fields = {normalise_header(x): x for x in reader.fieldnames if x is not None}
        missing = sorted(set(REQUIRED_SOURCE.values()) - set(fields))
        if missing:
            raise ValueError(f"CSV 缺少字段: {', '.join(missing)}")
        return [
            {key: row.get(fields[source], "") for key, source in REQUIRED_SOURCE.items()}
            for row in reader
        ]


def parse_number(value: str) -> float:
    value = value.strip()
    if not value:
        raise ValueError("empty")
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("not finite")
    return number


def clean_rows(rows: Iterable[dict[str, str]]) -> tuple[list[dict[str, object]], dict[str, int], Counter[str], Counter[str]]:
    stats = Counter()
    fruits: Counter[str] = Counter()
    labels: Counter[str] = Counter()
    output: list[dict[str, object]] = []
    for row in rows:
        stats["input_rows"] += 1
        fruit = row["fruit"].strip()
        label_key = row["class"].strip().lower()
        if not fruit or not label_key or any(not str(row[k]).strip() for k in NUMERIC_RANGES):
            stats["dropped_missing"] += 1
            continue
        try:
            values = {key: parse_number(row[key]) for key in NUMERIC_RANGES}
        except ValueError:
            stats["dropped_invalid_numeric"] += 1
            continue
        if any(not (low <= values[key] <= high) for key, (low, high) in NUMERIC_RANGES.items()):
            stats["dropped_out_of_range"] += 1
            continue
        if label_key not in LABELS:
            stats["dropped_invalid_label"] += 1
            continue
        label, label_name = LABELS[label_key]
        output.append({"fruit": fruit, **values, "label": label, "label_name": label_name})
        fruits[fruit] += 1
        labels[label_name] += 1
    stats["output_rows"] = len(output)
    return output, dict(stats), fruits, labels


def write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CANONICAL_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def run(input_path: Path, output_path: Path, report_path: Path, schema_path: Path) -> dict:
    source_rows = load_rows(input_path)
    rows, stats, fruits, labels = clean_rows(source_rows)
    write_csv(output_path, rows)
    report = {
        "source": {
            "path": str(input_path),
            "sha256": sha256(input_path),
            "has_timestamp": False,
            "source_columns": ["Fruit", "Temp", "Humid (%)", "Light (Fux)", "CO2 (pmm)", "Class"],
        },
        "canonical_columns": CANONICAL_COLUMNS,
        "label_mapping": {"Good": 0, "Bad": 1},
        "numeric_ranges": NUMERIC_RANGES,
        "stats": stats,
        "fruit_counts": dict(fruits),
        "label_counts": dict(labels),
        "output_sha256": sha256(output_path),
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    schema_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path.write_text(json.dumps({
        "dataset_type": "tabular_sensor_records",
        "has_timestamp": False,
        "columns": [
            {"name": "fruit", "type": "categorical"},
            {"name": "temp", "type": "float", "unit": "C"},
            {"name": "humid", "type": "float", "unit": "%"},
            {"name": "light", "type": "float", "unit": "lux"},
            {"name": "co2", "type": "float", "unit": "ppm"},
            {"name": "label", "type": "int", "values": [0, 1]},
            {"name": "label_name", "type": "categorical", "values": ["Good", "Bad"]},
        ],
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("data/raw/Dataset.csv"))
    parser.add_argument("--output", type=Path, default=Path("data/processed/cleaned_dataset.csv"))
    parser.add_argument("--report", type=Path, default=Path("evidence/data/cleaning_report.json"))
    parser.add_argument("--schema", type=Path, default=Path("data/processed/schema.json"))
    args = parser.parse_args()
    report = run(args.input, args.output, args.report, args.schema)
    print(json.dumps(report["stats"], ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
