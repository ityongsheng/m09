#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
python_bin=${M09_PYTHON:-python3}
out_dir=${1:-"$root/dist/local-model-exe"}
mkdir -p "$out_dir"
exec "$python_bin" -m PyInstaller --noconfirm --clean --onefile \
  --name m09-model-runner --paths "$root" \
  --distpath "$out_dir" --workpath /tmp/m09-pyinstaller-build \
  --specpath /tmp/m09-pyinstaller-spec "$root/ml/model_runner.py"
