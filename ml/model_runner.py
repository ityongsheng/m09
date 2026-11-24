#!/usr/bin/env python3
"""JSON stdin/stdout adapter used by the Spring Boot service.

The process accepts one sensor record object and returns one prediction object.
The model path is supplied with ``M09_MODEL_PATH`` so development, Docker and
the Windows packaged runner can use the same protocol.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

try:
    from .weighted_xgboost import WeightedXGBoostExperiment
except ImportError:  # direct execution from the project root
    from ml.weighted_xgboost import WeightedXGBoostExperiment


def main() -> int:
    raw = sys.stdin.read().strip()
    if not raw:
        raise ValueError("模型输入为空")
    request = json.loads(raw)
    if not isinstance(request, dict):
        raise ValueError("模型输入必须是一个 JSON 对象")
    model_path = Path(os.environ.get("M09_MODEL_PATH", "artifacts/model/weighted_xgboost.joblib"))
    experiment = WeightedXGBoostExperiment.load(model_path)
    result = experiment.predict([request], model="weighted")[0]
    payload = {
        "label": result["prediction"],
        "riskProbability": result["risk_probability"],
        "modelVersion": os.environ.get("M09_MODEL_VERSION", "weighted-xgboost-mi-v1"),
        "metricsJson": json.dumps(experiment.result().get("metrics", {}), ensure_ascii=False),
    }
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # keep the protocol deterministic for the Java caller
        print(json.dumps({"error": str(exc)}, ensure_ascii=False))
        raise SystemExit(1)
