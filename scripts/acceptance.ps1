param(
    [int]$Port = 8000,
    [string]$Username = "bekir",
    [switch]$NoStart
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$dataset = Join-Path $projectRoot "samples\general_evaluation.json"
$outputDirectory = Join-Path $projectRoot "output"
$healthUrl = "http://127.0.0.1:$Port/health"

if (-not (Test-Path $python -PathType Leaf)) {
    throw "Python ortami bulunamadi. Once .\scripts\setup.ps1 calistir."
}
if (-not (Test-Path $dataset -PathType Leaf)) {
    throw "Genel kabul veri kumesi bulunamadi: $dataset"
}

Set-Location $projectRoot

if (-not $NoStart) {
    & (Join-Path $PSScriptRoot "start.ps1") -Port $Port -NoBrowser
}

$health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 5
if ($health.status -ne "alive") {
    throw "DersAtlas saglik denetimi basarisiz: $healthUrl"
}

New-Item -ItemType Directory -Path $outputDirectory -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$report = Join-Path $outputDirectory "agent-acceptance-$stamp.json"

Write-Host "Kabul testi basliyor. DersAtlas giris parolasi ekranda gorunmez." -ForegroundColor Cyan
& $python (Join-Path $PSScriptRoot "evaluate.py") `
    --url "http://127.0.0.1:$Port" `
    --username $Username `
    --mode agent `
    --with-generation `
    --dataset $dataset `
    --output $report

if ($LASTEXITCODE -ne 0) {
    throw "Kabul testi basarisiz oldu. Yukaridaki tanilamayi kontrol et."
}

$result = Get-Content $report -Raw -Encoding UTF8 | ConvertFrom-Json
Write-Host "Kabul raporu hazir: $report" -ForegroundColor Green
Write-Host "Hazir kaynakta uygulama dogrulugu: $($result.summary.application_accuracy_on_ready_corpus)"
Write-Host "Ortanca sure (p50): $($result.summary.p50_ms) ms"
Write-Host "p95 sure: $($result.summary.p95_ms) ms"
