#!/usr/bin/env bash
set -euo pipefail

# Upload the real CSV to HDFS, download it for the deterministic cleaner, and
# upload the cleaned result. This script never fabricates rows or labels.
PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
RAW_LOCAL="${RAW_LOCAL:-$PROJECT_ROOT/data/raw/Dataset.csv}"
CLEAN_LOCAL="${CLEAN_LOCAL:-$PROJECT_ROOT/data/processed/cleaned_dataset.csv}"
HDFS_ROOT="${HDFS_ROOT:-/m09/cold-storage}"
HDFS_BIN="${HDFS_BIN:-hdfs}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
WORK_DIR="${WORK_DIR:-$PROJECT_ROOT/evidence/hadoop/run}"

if [[ "$HDFS_BIN" == "hdfs" && -n "${HADOOP_HOME:-}" && -x "$HADOOP_HOME/bin/hdfs" ]]; then
  HDFS_BIN="$HADOOP_HOME/bin/hdfs"
fi

if [[ ! -f "$RAW_LOCAL" ]]; then
  echo "raw dataset not found: $RAW_LOCAL" >&2
  exit 2
fi
command -v "$HDFS_BIN" >/dev/null 2>&1 || {
  echo "HDFS command not found; install/start a Hadoop pseudo-distributed environment before running this script" >&2
  exit 3
}
mkdir -p "$WORK_DIR" "$PROJECT_ROOT/data/processed"

"$HDFS_BIN" dfs -mkdir -p "$HDFS_ROOT/raw" "$HDFS_ROOT/processed"
"$HDFS_BIN" dfs -put -f "$RAW_LOCAL" "$HDFS_ROOT/raw/Dataset.csv"
"$HDFS_BIN" dfs -cat "$HDFS_ROOT/raw/Dataset.csv" > "$WORK_DIR/raw_from_hdfs.csv"
"$PYTHON_BIN" "$PROJECT_ROOT/pipeline/etl/clean_dataset.py" \
  --input "$WORK_DIR/raw_from_hdfs.csv" \
  --output "$CLEAN_LOCAL" \
  --report "$WORK_DIR/cleaning_report.json" \
  --schema "$PROJECT_ROOT/data/processed/schema.json"
"$HDFS_BIN" dfs -put -f "$CLEAN_LOCAL" "$HDFS_ROOT/processed/cleaned_dataset.csv"
"$HDFS_BIN" dfs -put -f "$PROJECT_ROOT/data/processed/schema.json" "$HDFS_ROOT/processed/schema.json"
"$HDFS_BIN" dfs -put -f "$WORK_DIR/cleaning_report.json" "$HDFS_ROOT/processed/cleaning_report.json"
"$HDFS_BIN" dfs -ls "$HDFS_ROOT/raw" "$HDFS_ROOT/processed" | tee "$WORK_DIR/hdfs_listing.txt"
