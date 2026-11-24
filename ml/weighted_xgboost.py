from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

import joblib
import numpy as np
import pandas as pd
from sklearn.feature_selection import mutual_info_classif
from sklearn.metrics import (
    accuracy_score,
    f1_score,
    mean_absolute_error,
    mean_squared_error,
    precision_score,
    r2_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


@dataclass(frozen=True)
class ExperimentConfig:
    target_column: str = "label"
    categorical_columns: tuple[str, ...] = ("fruit",)
    test_size: float = 0.2
    random_state: int = 20261122
    mi_epsilon: float = 1e-6
    threshold: float = 0.5
    n_estimators: int = 160
    max_depth: int = 4
    learning_rate: float = 0.08
    subsample: float = 0.9
    colsample_bytree: float = 0.9


class WeightedXGBoostExperiment:
    """Train baseline and mutual-information weighted XGBoost classifiers.

    The weighted model uses MI computed on the training split only. Features at
    or above the training MI median are retained, then each retained feature is
    multiplied by ``(MI + epsilon) / (mean(MI) + epsilon)``. This makes the
    weighting rule explicit, reproducible, and independent of the test split.
    """

    def __init__(self, config: ExperimentConfig | None = None) -> None:
        self.config = config or ExperimentConfig()
        self.feature_columns_: list[str] = []
        self.numeric_columns_: list[str] = []
        self.category_values_: dict[str, list[str]] = {}
        self.scaler_: StandardScaler | None = None
        self.mi_scores_: dict[str, float] = {}
        self.selected_features_: list[str] = []
        self.feature_weights_: dict[str, float] = {}
        self.baseline_model_: XGBClassifier | None = None
        self.weighted_model_: XGBClassifier | None = None
        self.metrics_: dict[str, dict[str, float | None]] = {}
        self.split_summary_: dict[str, int] = {}

    @staticmethod
    def _normalise_label(value: Any) -> int:
        if isinstance(value, str):
            value = value.strip().lower()
            if value in {"good", "0", "normal", "false", "否"}:
                return 0
            if value in {"bad", "1", "risk", "true", "是"}:
                return 1
        if value in (0, 0.0, False):
            return 0
        if value in (1, 1.0, True):
            return 1
        raise ValueError(f"无法将标签转换为 Good/Bad 二分类: {value!r}")

    def _validate_frame(self, frame: pd.DataFrame, require_target: bool = True) -> pd.DataFrame:
        if not isinstance(frame, pd.DataFrame):
            frame = pd.DataFrame(frame)
        if frame.empty:
            raise ValueError("输入数据为空")
        frame = self._canonicalise_columns(frame)
        if require_target and self.config.target_column not in frame.columns:
            raise ValueError(f"缺少目标列 {self.config.target_column!r}")
        if require_target:
            frame = frame.copy()
            frame[self.config.target_column] = frame[self.config.target_column].map(self._normalise_label)
            if frame[self.config.target_column].nunique() < 2:
                raise ValueError("训练数据必须同时包含 Good 和 Bad 两类")
        return frame

    def _canonicalise_columns(self, frame: pd.DataFrame) -> pd.DataFrame:
        """Accept the raw Mendeley names and the cleaned lowercase schema.

        The ETL output is the runtime contract (`fruit`, `temp`, ..., `label`),
        while the source CSV and early fixtures use title case (`Fruit`,
        `Class`).  Resolve those aliases once at the model boundary so the
        training and prediction paths cannot silently diverge.
        """
        aliases = {
            self.config.target_column: (self.config.target_column, "label", "class", "Class"),
            **{
                column: (column, column.lower(), column.title())
                for column in self.config.categorical_columns
            },
        }
        rename: dict[str, str] = {}
        lowered = {str(column).lower(): column for column in frame.columns}
        for canonical, candidates in aliases.items():
            if canonical in frame.columns:
                continue
            for candidate in candidates:
                source = lowered.get(candidate.lower())
                if source is not None and source not in rename:
                    rename[source] = canonical
                    break
        return frame.rename(columns=rename)

    def _fit_encoder(self, frame: pd.DataFrame) -> None:
        excluded = {self.config.target_column}
        self.feature_columns_ = [str(c) for c in frame.columns if c not in excluded]
        if not self.feature_columns_:
            raise ValueError("没有可用特征列")
        self.numeric_columns_ = [
            c for c in self.feature_columns_ if c not in self.config.categorical_columns
        ]
        self.category_values_ = {}
        for column in self.config.categorical_columns:
            if column in frame.columns:
                values = frame[column].fillna("<MISSING>").astype(str).unique().tolist()
                self.category_values_[column] = sorted(values)

    def _encode(self, frame: pd.DataFrame) -> tuple[np.ndarray, list[str]]:
        data = frame.copy()
        parts: list[pd.DataFrame] = []
        names: list[str] = []
        for column in self.feature_columns_:
            if column in self.config.categorical_columns and column in self.category_values_:
                series = data[column].fillna("<MISSING>").astype(str) if column in data else pd.Series("<MISSING>", index=data.index)
                values = pd.DataFrame(index=data.index)
                for category in self.category_values_[column]:
                    name = f"{column}={category}"
                    values[name] = (series == category).astype(float)
                    names.append(name)
                parts.append(values)
            else:
                series = pd.to_numeric(data[column], errors="coerce") if column in data else pd.Series(np.nan, index=data.index)
                series = series.fillna(0.0).astype(float)
                parts.append(pd.DataFrame({column: series}, index=data.index))
                names.append(column)
        encoded = pd.concat(parts, axis=1)
        return encoded.to_numpy(dtype=float), names

    @staticmethod
    def _safe_metric(fn, *args, **kwargs) -> float | None:
        try:
            value = float(fn(*args, **kwargs))
            return value if np.isfinite(value) else None
        except (ValueError, ZeroDivisionError):
            return None

    def _metrics(self, y_true: np.ndarray, probability: np.ndarray) -> dict[str, float | None]:
        prediction = (probability >= self.config.threshold).astype(int)
        return {
            "accuracy": self._safe_metric(accuracy_score, y_true, prediction),
            "precision": self._safe_metric(precision_score, y_true, prediction, zero_division=0),
            "recall": self._safe_metric(recall_score, y_true, prediction, zero_division=0),
            "f1": self._safe_metric(f1_score, y_true, prediction, zero_division=0),
            "roc_auc": self._safe_metric(roc_auc_score, y_true, probability),
            "mse": self._safe_metric(mean_squared_error, y_true, probability),
            "mae": self._safe_metric(mean_absolute_error, y_true, probability),
            "r2": self._safe_metric(r2_score, y_true, probability),
        }

    def _model(self) -> XGBClassifier:
        return XGBClassifier(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            learning_rate=self.config.learning_rate,
            subsample=self.config.subsample,
            colsample_bytree=self.config.colsample_bytree,
            objective="binary:logistic",
            eval_metric="logloss",
            random_state=self.config.random_state,
            n_jobs=1,
            tree_method="hist",
        )

    def fit(self, frame: pd.DataFrame) -> "WeightedXGBoostExperiment":
        frame = self._validate_frame(frame, require_target=True)
        self._fit_encoder(frame.drop(columns=[self.config.target_column]))
        x, encoded_names = self._encode(frame)
        y = frame[self.config.target_column].to_numpy(dtype=int)
        x_train, x_test, y_train, y_test = train_test_split(
            x,
            y,
            test_size=self.config.test_size,
            random_state=self.config.random_state,
            stratify=y,
        )
        self.split_summary_ = {
            "train_rows": int(len(y_train)),
            "test_rows": int(len(y_test)),
            "total_rows": int(len(y)),
        }
        self.scaler_ = StandardScaler().fit(x_train)
        x_train_scaled = self.scaler_.transform(x_train)
        x_test_scaled = self.scaler_.transform(x_test)

        mi = mutual_info_classif(
            x_train_scaled,
            y_train,
            discrete_features=False,
            random_state=self.config.random_state,
        )
        self.mi_scores_ = {name: float(score) for name, score in zip(encoded_names, mi)}
        median = float(np.median(mi))
        selected_indices = np.flatnonzero(mi >= median)
        if selected_indices.size == 0:
            selected_indices = np.array([int(np.argmax(mi))])
        self.selected_features_ = [encoded_names[i] for i in selected_indices]
        selected_mi = mi[selected_indices]
        mean_mi = float(np.mean(selected_mi))
        weights = (selected_mi + self.config.mi_epsilon) / (mean_mi + self.config.mi_epsilon)
        self.feature_weights_ = {
            name: float(weight) for name, weight in zip(self.selected_features_, weights)
        }

        self.baseline_model_ = self._model().fit(x_train_scaled, y_train)
        weighted_train = x_train_scaled[:, selected_indices] * weights
        weighted_test = x_test_scaled[:, selected_indices] * weights
        self.weighted_model_ = self._model().fit(weighted_train, y_train)
        self.metrics_ = {
            "baseline": self._metrics(y_test, self.baseline_model_.predict_proba(x_test_scaled)[:, 1]),
            "weighted": self._metrics(y_test, self.weighted_model_.predict_proba(weighted_test)[:, 1]),
        }
        self._encoded_names_ = encoded_names
        return self

    def _require_fitted(self) -> None:
        if self.scaler_ is None or self.weighted_model_ is None or self.baseline_model_ is None:
            raise RuntimeError("模型尚未训练")

    def _transform_for_inference(self, frame: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
        self._require_fitted()
        x, names = self._encode(frame)
        # _encode is deterministic after fitting; fail loudly if the schema changed.
        if names != self._encoded_names_:
            raise ValueError("输入字段编码与训练模型不一致")
        scaled = self.scaler_.transform(x)
        indices = [self._encoded_names_.index(name) for name in self.selected_features_]
        weights = np.array([self.feature_weights_[name] for name in self.selected_features_])
        return scaled, scaled[:, indices] * weights

    def predict(self, records: pd.DataFrame | Iterable[Mapping[str, Any]], model: str = "weighted") -> list[dict[str, Any]]:
        frame = self._validate_frame(pd.DataFrame(records), require_target=False)
        baseline_x, weighted_x = self._transform_for_inference(frame)
        selected = self.weighted_model_ if model == "weighted" else self.baseline_model_
        values = weighted_x if model == "weighted" else baseline_x
        probability = selected.predict_proba(values)[:, 1]
        label = np.where(probability >= self.config.threshold, "Bad", "Good")
        return [
            {
                "prediction": str(lbl),
                "risk_probability": round(float(prob), 8),
                "model": model,
            }
            for lbl, prob in zip(label, probability)
        ]

    def result(self) -> dict[str, Any]:
        return {
            "config": asdict(self.config),
            "split": self.split_summary_,
            "mi_scores": self.mi_scores_,
            "selected_features": self.selected_features_,
            "feature_weights": self.feature_weights_,
            "metrics": self.metrics_,
            "target_mapping": {"Good": 0, "Bad": 1},
            "metric_roles": {
                "primary": ["accuracy", "precision", "recall", "f1", "roc_auc"],
                "auxiliary": ["mse", "mae", "r2"],
            },
        }

    def save(self, path: str | Path, result_path: str | Path | None = None) -> None:
        self._require_fitted()
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path)
        if result_path:
            result_path = Path(result_path)
            result_path.parent.mkdir(parents=True, exist_ok=True)
            result_path.write_text(json.dumps(self.result(), ensure_ascii=False, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: str | Path) -> "WeightedXGBoostExperiment":
        obj = joblib.load(path)
        if not isinstance(obj, cls):
            raise TypeError("模型文件不是 WeightedXGBoostExperiment")
        return obj
