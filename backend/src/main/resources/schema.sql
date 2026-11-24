CREATE TABLE IF NOT EXISTS sensor_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  fruit TEXT NOT NULL,
  temp REAL NOT NULL,
  humid REAL NOT NULL,
  light REAL NOT NULL,
  co2 REAL NOT NULL,
  source TEXT,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS prediction_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sensor_record_id INTEGER,
  label TEXT NOT NULL,
  risk_probability REAL NOT NULL,
  model_version TEXT NOT NULL,
  metrics_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY(sensor_record_id) REFERENCES sensor_record(id)
);
CREATE TABLE IF NOT EXISTS alert_record (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  prediction_id INTEGER NOT NULL,
  level TEXT NOT NULL,
  message TEXT NOT NULL,
  status TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY(prediction_id) REFERENCES prediction_record(id)
);
CREATE TABLE IF NOT EXISTS experiment_metric (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  model_name TEXT NOT NULL,
  accuracy REAL,
  precision_value REAL,
  recall_value REAL,
  f1 REAL,
  roc_auc REAL,
  mse REAL,
  mae REAL,
  r2 REAL,
  config_json TEXT,
  created_at TEXT NOT NULL
);
