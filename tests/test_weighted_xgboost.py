import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from ml.weighted_xgboost import WeightedXGBoostExperiment


class WeightedXGBoostTest(unittest.TestCase):
    @staticmethod
    def fixture() -> pd.DataFrame:
        rows = []
        for i in range(80):
            bad = i % 2
            rows.append({
                "Fruit": ["Orange", "Banana", "Tomato", "Pineapple"][i % 4],
                "Temp": 2.0 + bad * 9 + (i % 5) * 0.1,
                "Humid": 65 + bad * 25 + (i % 3),
                "Light": 20 + (i % 7),
                "CO2": 350 + bad * 600 + i,
                "Class": "Bad" if bad else "Good",
            })
        return pd.DataFrame(rows)

    def test_train_and_metrics(self):
        exp = WeightedXGBoostExperiment().fit(self.fixture())
        result = exp.result()
        self.assertEqual(result["split"]["total_rows"], 80)
        self.assertTrue(result["selected_features"])
        self.assertIn("weighted", result["metrics"])
        self.assertIsNotNone(result["metrics"]["weighted"]["f1"])
        self.assertEqual(result["metric_roles"]["primary"][0], "accuracy")

    def test_save_load_predict_json(self):
        exp = WeightedXGBoostExperiment().fit(self.fixture())
        with tempfile.TemporaryDirectory() as tmp:
            model_path = Path(tmp) / "model.joblib"
            metrics_path = Path(tmp) / "metrics.json"
            exp.save(model_path, metrics_path)
            loaded = WeightedXGBoostExperiment.load(model_path)
            output = loaded.predict(self.fixture().drop(columns=["Class"]).head(2).to_dict("records"))
            self.assertEqual(len(output), 2)
            self.assertIn(output[0]["prediction"], {"Good", "Bad"})
            json.loads(metrics_path.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
