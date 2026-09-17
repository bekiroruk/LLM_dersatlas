$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) { throw "Önce setup.ps1 veya README kurulumu gerekli." }
& ".venv\Scripts\python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 1 --no-access-log
