param([string]$VenvPath = (Join-Path $PSScriptRoot '.venv'))
$ErrorActionPreference = 'Stop'
py -3.12 -m venv $VenvPath
if ($LASTEXITCODE -ne 0) { throw 'Install Python 3.12 first.' }
$python = Join-Path $VenvPath 'Scripts\python.exe'
& $python -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'Could not update pip.' }
& $python -m pip install -r (Join-Path $PSScriptRoot 'requirements.txt')
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python -m pip check
if ($LASTEXITCODE -ne 0) { throw 'Incompatible dependencies.' }
& $python (Join-Path $PSScriptRoot 'verify_models.py')
if ($LASTEXITCODE -ne 0) { throw 'Run git lfs pull, then verify_models.py again.' }
Write-Host "Ready. Python: $python"
