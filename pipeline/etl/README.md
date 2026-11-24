# 数据清洗

```bash
python3 pipeline/etl/clean_dataset.py
```

默认读取 `data/raw/Dataset.csv`，输出 `data/processed/cleaned_dataset.csv`、`data/processed/schema.json` 和 `evidence/data/cleaning_report.json`。

源数据是无时间戳的冷库传感器记录表。清洗程序只删除缺失、非数值、超出物理范围或未知标签的记录，并将 `Good/Bad` 映射为 `0/1`；不会生成模拟记录。
