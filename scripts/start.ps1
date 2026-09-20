param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = (Join-Path $projectRoot ".venv\Scripts\python.exe")
$healthUrl = "http://127.0.0.1:$Port/health"

if (-not (Test-Path $python -PathType Leaf)) {
    throw "Python ortamı bulunamadı. Önce .\scripts\setup.ps1 çalıştır."
}

Set-Location $projectRoot

# Yalnızca bu projenin sanal ortamıyla açılmış DersAtlas sunucularını durdur.
# Böylece gömülü Qdrant kilidi ve eski kodu sunan görünmez Uvicorn süreci kalmaz.
$servers = @(
    Get-CimInstance Win32_Process | Where-Object {
        $command = [string]$_.CommandLine
        $executable = [string]$_.ExecutablePath
        ($executable -ieq $python -or $command -like "*$projectRoot*") -and
        $command -match "uvicorn\s+app\.main:app"
    }
)

foreach ($server in $servers) {
    Stop-Process -Id $server.ProcessId -Force -ErrorAction SilentlyContinue
}

if ($servers.Count -gt 0) {
    Start-Sleep -Milliseconds 700
}

$listeners = @(
    Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
)
if ($listeners.Count -gt 0) {
    $owners = ($listeners | Select-Object -ExpandProperty OwningProcess -Unique) -join ", "
    throw "127.0.0.1:$Port başka bir süreç tarafından kullanılıyor (PID: $owners). O süreci kapat veya -Port ile başka port seç."
}

$revision = (& $python -c "from app.rag import RAG_REVISION; print(RAG_REVISION)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $revision) {
    throw "DersAtlas kodu yüklenemedi. Terminal çıktısındaki Python hatasını kontrol et."
}

$logDirectory = Join-Path $projectRoot "data\logs"
New-Item -ItemType Directory -Path $logDirectory -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$stdoutLog = Join-Path $logDirectory "server-$stamp.out.log"
$stderrLog = Join-Path $logDirectory "server-$stamp.err.log"

$arguments = @(
    "-m", "uvicorn", "app.main:app",
    "--host", "127.0.0.1",
    "--port", [string]$Port,
    "--workers", "1",
    "--no-access-log"
)

$process = Start-Process `
    -FilePath $python `
    -ArgumentList $arguments `
    -WorkingDirectory $projectRoot `
    -RedirectStandardOutput $stdoutLog `
    -RedirectStandardError $stderrLog `
    -PassThru

$pidFile = Join-Path $projectRoot "data\server.pid"
Set-Content -Path $pidFile -Value ([string]$process.Id) -Encoding Ascii

$health = $null
for ($attempt = 0; $attempt -lt 80; $attempt++) {
    Start-Sleep -Milliseconds 500
    if ($process.HasExited) {
        $details = ""
        if (Test-Path $stderrLog) {
            $details = (Get-Content $stderrLog -Tail 25 -ErrorAction SilentlyContinue) -join [Environment]::NewLine
        }
        throw "DersAtlas başlatılamadı.`n$details"
    }
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 2
        if ($health.status -eq "alive") {
            break
        }
    }
    catch {
        $health = $null
    }
}

if ($null -eq $health -or $health.status -ne "alive") {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "DersAtlas 40 saniye içinde hazır olmadı. Günlük: $stderrLog"
}

if ([string]$health.rag_revision -ne $revision) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "Yanlış sunucu sürümü açıldı. Beklenen: $revision; çalışan: $($health.rag_revision)"
}

Write-Host "DersAtlas hazır: http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "RAG sürümü: $revision"
Write-Host "Sunucu PID: $($process.Id)"
Write-Host "Hata günlüğü: $stderrLog"

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$Port"
}
