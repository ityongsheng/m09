from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from .weighted_xgboost import WeightedXGBoostExperiment


def train(args: argparse.Namespace) -> None:
    frame = pd.read_csv(args.input)
    experiment = WeightedXGBoostExperiment().fit(frame)
    experiment.save(args.model, args.metrics)
    print(json.dumps(experiment.result(), ensure_ascii=False, indent=2))


def predict(args: argparse.Namespace) -> None:
    experiment = WeightedXGBoostExperiment.load(args.model)
    source = json.loads(Path(args.input).read_text(encoding="utf-8"))
    records = source if isinstance(source, list) else source.get("records", [source])
    result = experiment.predict(records, model=args.model_type)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description="m09 XGBoost model CLI")
    sub = parser.add_subparsers(dest="command", required=True)
    train_parser = sub.add_parser("train")
    train_parser.add_argument("--input", required=True)
    train_parser.add_argument("--model", required=True)
    train_parser.add_argument("--metrics", required=True)
    train_parser.set_defaults(func=train)
    predict_parser = sub.add_parser("predict")
    predict_parser.add_argument("--model", required=True)
    predict_parser.add_argument("--input", required=True)
    predict_parser.add_argument("--model-type", choices=["weighted", "baseline"], default="weighted")
    predict_parser.set_defaults(func=predict)
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
