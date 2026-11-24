# 模型模块

训练：

```bash
python -m ml.cli train --input data/processed/cleaned_dataset.csv \
  --model artifacts/model/weighted_xgboost.joblib \
  --metrics evidence/models/metrics.json
```

预测：

```bash
python -m ml.cli predict --model artifacts/model/weighted_xgboost.joblib \
  --input request.json
```

模型在训练集上计算互信息并按训练集互信息中位数筛选特征。加权输入使用
`(MI + 1e-6) / (mean(MI) + 1e-6)` 缩放，测试集只用于最终评价。
