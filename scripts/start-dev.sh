#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$root/runtime"
: "${M09_PYTHON:=$root/.venv/bin/python}"
: "${M09_MODEL_PATH:=$root/artifacts/model/weighted_xgboost.joblib}"
: "${M09_MODEL_COMMAND:=$root/scripts/run_model.sh}"
: "${M09_DB_PATH:=$root/runtime/m09.sqlite}"
export M09_PYTHON M09_MODEL_PATH M09_MODEL_COMMAND M09_DB_PATH
exec mvn -f "$root/backend/pom.xml" spring-boot:run
