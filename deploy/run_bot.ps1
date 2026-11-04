<#
.SYNOPSIS
  Keeps the UZEX Telegram bot running on Windows: restarts bot.py whenever it exits.

.DESCRIPTION
  Run from anywhere:   powershell -ExecutionPolicy Bypass -File deploy\run_bot.ps1
  Stop with Ctrl+C (the loop and the child python process both stop).

  - Works from the repository root (resolved from this script's location).
  - Uses .venv\Scripts\python.exe if it exists, otherwise `python` from PATH.
  - Every line the bot prints is written to logs\bot.log with a timestamp (and echoed to the console).
  - Waits RestartDelaySec between restarts so a broken config does not spin at 100% CPU.

.PARAMETER RestartDelaySec
  Seconds to wait before restarting after the bot exits (default 5).
#>
param(
    [int]$RestartDelaySec = 5
)

$ErrorActionPreference = "Continue"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

New-Item -ItemType Directory -Force -Path (Join-Path $root "logs") | Out-Null
$logFile = Join-Path $root "logs\bot.log"

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUNBUFFERED = "1"

$python = Join-Path $root ".venv\Scripts\python.exe"
if (-not (Test-Path $python)) { $python = "python" }

function Write-Log([string]$Message) {
    $line = "{0} {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $Message
    Add-Content -Path $logFile -Value $line -Encoding utf8
    Write-Host $line
}

if (-not (Test-Path (Join-Path $root ".env"))) {
    Write-Log "WARNING: .env not found in $root (copy .env.example and fill in the keys)"
}
if (-not (Test-Path (Join-Path $root "data\uzex.db"))) {
    Write-Log "WARNING: data\uzex.db not found - run: python -X utf8 scripts\build_db.py"
}

Write-Log "supervisor started in $root using $python (Ctrl+C to stop)"
try {
    while ($true) {
        Write-Log "starting bot.py"
        & $python -X utf8 bot.py 2>&1 | ForEach-Object { Write-Log ([string]$_) }
        $code = $LASTEXITCODE
        Write-Log "bot.py exited with code $code; restarting in $RestartDelaySec s"
        Start-Sleep -Seconds $RestartDelaySec
    }
}
finally {
    Write-Log "supervisor stopped"
}
