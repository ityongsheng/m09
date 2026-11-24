#!/bin/sh
set -eu
project_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_bin=${M09_PYTHON:-python3}
exec "$python_bin" "$project_root/ml/model_runner.py"
