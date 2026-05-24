# UiPath + Agentic AI 팀 데모 (한 번에 실행)
# 사용: demo 폴더에서  .\scripts\run_team_demo.ps1

$ErrorActionPreference = "Stop"
$DemoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $DemoRoot

Write-Host "`n=== Atlas Medical Team Demo ===" -ForegroundColor Cyan
Write-Host "Folder: $DemoRoot`n"

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found. Install Python 3.10+" -ForegroundColor Red
    exit 1
}

$env:PYTHONIOENCODING = "utf-8"

if (-not (Test-Path ".venv")) {
    Write-Host "[1/3] Creating venv..." -ForegroundColor Yellow
    python -m venv .venv
}

Write-Host "[2/3] Installing packages..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

Write-Host "[3/3] Running pipeline (normal case)..." -ForegroundColor Yellow
& .\.venv\Scripts\python.exe run_standalone.py

Write-Host "`n--- High risk sample (UiPath If branch: 재검토_필요=True) ---" -ForegroundColor Magenta
& .\.venv\Scripts\python.exe run_high_risk_demo.py

Write-Host "`n=== Next: API server for UiPath ===" -ForegroundColor Green
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  uvicorn app.main:app --reload --port 8000"
Write-Host "  Swagger: http://localhost:8000/docs"
Write-Host "  UiPath HTTP POST -> http://localhost:8000/analyze`n"
