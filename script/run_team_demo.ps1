# 팀 데모: FastAPI 기동 후 샘플 파이프라인 2회 호출
# 사용: .\script\run_team_demo.ps1

$ErrorActionPreference = "Stop"
$DemoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $DemoRoot

Write-Host "`n=== Atlas Medical Team Demo ===" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found. Install Python 3.10+" -ForegroundColor Red
    exit 1
}

$env:PYTHONIOENCODING = "utf-8"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

$port = 8000
$base = "http://127.0.0.1:$port"
$uvicorn = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $port `
    -PassThru -WindowStyle Hidden

try {
    Start-Sleep -Seconds 4
    Write-Host "[1/2] POST /demo/pipeline?sample=normal" -ForegroundColor Yellow
    Invoke-RestMethod -Method Post -Uri "$base/demo/pipeline?sample=normal" | Out-Null
    Write-Host "[2/2] POST /demo/pipeline?sample=high_risk (HIDL)" -ForegroundColor Magenta
    Invoke-RestMethod -Method Post -Uri "$base/demo/pipeline?sample=high_risk" | Out-Null
    Write-Host "`n[OK] Check terminal/Render Logs for [SUCCESS] / [ADMIN] lines" -ForegroundColor Green
    Write-Host "Swagger: $base/docs`n"
} finally {
    Stop-Process -Id $uvicorn.Id -Force -ErrorAction SilentlyContinue
}
