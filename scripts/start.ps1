param(
    [int]$Port = 8000,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = (Join-Path $projectRoot ".venv\Scripts\python.exe")
$healthUrl = "http://127.0.0.1:$Port/health"

if (-not (Test-Path $python -PathType Leaf)) {
    throw "Python ortami bulunamadi. Once .\scripts\setup.ps1 calistir."
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
    throw "127.0.0.1:$Port baska bir surec tarafindan kullaniliyor (PID: $owners). O sureci kapat veya -Port ile baska port sec."
}

$revision = (& $python -c "from app.rag import RAG_REVISION; print(RAG_REVISION)").Trim()
if ($LASTEXITCODE -ne 0 -or -not $revision) {
    throw "DersAtlas kodu yuklenemedi. Terminal ciktisindaki Python hatasini kontrol et."
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
        $process.WaitForExit()
        Start-Sleep -Milliseconds 200
        $details = @()
        if (Test-Path $stderrLog) {
            $stderrDetails = (Get-Content $stderrLog -Tail 50 -Encoding UTF8 -ErrorAction SilentlyContinue) -join [Environment]::NewLine
            if ($stderrDetails) {
                $details += "STDERR:`n$stderrDetails"
            }
        }
        if (Test-Path $stdoutLog) {
            $stdoutDetails = (Get-Content $stdoutLog -Tail 50 -Encoding UTF8 -ErrorAction SilentlyContinue) -join [Environment]::NewLine
            if ($stdoutDetails) {
                $details += "STDOUT:`n$stdoutDetails"
            }
        }
        if ($details.Count -eq 0) {
            $details += "Sunucu gunluk uretmeden kapandi."
        }
        $diagnostic = $details -join [Environment]::NewLine
        throw "DersAtlas baslatilamadi (cikis kodu: $($process.ExitCode)).`n$diagnostic`nHata gunlugu: $stderrLog`nCikti gunlugu: $stdoutLog"
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
    throw "DersAtlas 40 saniye icinde hazir olmadi. Gunluk: $stderrLog"
}

if ([string]$health.rag_revision -ne $revision) {
    Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue
    throw "Yanlis sunucu surumu acildi. Beklenen: $revision; calisan: $($health.rag_revision)"
}

Write-Host "DersAtlas hazir: http://127.0.0.1:$Port" -ForegroundColor Green
Write-Host "RAG surumu: $revision"
Write-Host "Sunucu PID: $($process.Id)"
Write-Host "Hata gunlugu: $stderrLog"

if (-not $NoBrowser) {
    Start-Process "http://127.0.0.1:$Port"
}
