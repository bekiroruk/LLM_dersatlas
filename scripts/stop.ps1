$ErrorActionPreference = "Stop"
$projectRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$stopped = @()

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
    $stopped += $server.ProcessId
}

$pidFile = Join-Path $projectRoot "data\server.pid"
if (Test-Path $pidFile) {
    Remove-Item $pidFile -Force
}

if ($stopped.Count -eq 0) {
    Write-Host "Bu proje için çalışan DersAtlas sunucusu bulunamadı."
}
else {
    Write-Host "DersAtlas durduruldu (PID: $($stopped -join ', '))." -ForegroundColor Green
}
