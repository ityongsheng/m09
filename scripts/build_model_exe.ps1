$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
$python = if ($env:M09_PYTHON) { $env:M09_PYTHON } else { 'python' }
$out = Join-Path $root 'dist\windows-model-exe'
New-Item -ItemType Directory -Force -Path $out | Out-Null
& $python -m PyInstaller --noconfirm --clean --onefile `
  --name m09-model-runner --paths $root `
  --collect-all xgboost `
  --distpath $out --workpath (Join-Path $env:TEMP 'm09-pyinstaller-build') `
  --specpath (Join-Path $env:TEMP 'm09-pyinstaller-spec') `
  (Join-Path $root 'ml\model_runner.py')
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
