$ErrorActionPreference = "Stop"
$projectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $projectRoot
if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -3.12 -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Python 3.12 kurulumu gerekli." }
}
& ".venv\Scripts\python.exe" -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Paket kurulumu tamamlanamadı." }
if (-not (Test-Path ".env")) { Copy-Item ".env.example" ".env" }
Write-Host "Paketler hazır. README içindeki Ollama/model ve kullanıcı oluşturma adımlarını tamamla."
