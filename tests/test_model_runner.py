import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


try:
    import pandas as pd
    from ml.weighted_xgboost import WeightedXGBoostExperiment
except ImportError:  # The base system Python may not have model dependencies.
    pd = None
    WeightedXGBoostExperiment = None


@unittest.skipUnless(pd is not None, "模型依赖未安装；使用项目 Python 环境运行此集成检查")
class ModelRunnerContractTest(unittest.TestCase):
    def test_json_stdin_stdout_contract(self):
        root = Path(__file__).resolve().parents[1]
        frame = pd.read_csv(root / "data/processed/cleaned_dataset.csv")
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            model_path = tmp_path / "model.joblib"
            WeightedXGBoostExperiment().fit(frame).save(model_path)
            request = {
                "fruit": "Orange",
                "temp": 22,
                "humid": 95,
                "light": 7.3,
                "co2": 361,
            }
            env = dict(os.environ, M09_MODEL_PATH=str(model_path))
            result = subprocess.run(
                [sys.executable, str(root / "ml/model_runner.py")],
                input=json.dumps(request),
                text=True,
                capture_output=True,
                check=True,
                env=env,
            )
            payload = json.loads(result.stdout)
            self.assertIn(payload["label"], {"Good", "Bad"})
            self.assertGreaterEqual(payload["riskProbability"], 0.0)
            self.assertLessEqual(payload["riskProbability"], 1.0)
            self.assertTrue(payload["modelVersion"])


if __name__ == "__main__":
    unittest.main()
