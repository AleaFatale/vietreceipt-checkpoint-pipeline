param([string]$Image, [string]$Out, [string]$Python = (Join-Path $PSScriptRoot '.venv\Scripts\python.exe'), [switch]$OpenReport)
$ErrorActionPreference = 'Stop'
$runArgs = @('-X','utf8',(Join-Path $PSScriptRoot 'run.py'))
if ($Image) { $runArgs += @('--image',$Image) }
if ($Out) { $runArgs += @('--out',$Out) }
if ($OpenReport) { $runArgs += '--open' }
& $Python @runArgs
if ($LASTEXITCODE -ne 0) { throw 'Pipeline failed. Read the saved stage logs.' }
