# Demo1: consult 수집·인계·(선택) Agentic·Render API
# 사용:
#   .\script\run_demo1.ps1
#   .\script\run_demo1.ps1 -Render -Pipeline
#   .\script\run_demo1.ps1 -Source api -Image "C:\path\pill.jpg"

param(
    [ValidateSet("normal", "high_risk")]
    [string]$Sample = "normal",
    [ValidateSet("fixture", "input_json", "api")]
    [string]$Source = "fixture",
    [string]$Image = "",
    [string]$Audio = "",
    [switch]$Pipeline,
    [switch]$Render,
    [switch]$ServerOnly
)

$ErrorActionPreference = "Stop"
$DemoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $DemoRoot

Write-Host "`n=== Demo1 (consult -> handoff -> agentic) ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
$env:PYTHONIOENCODING = "utf-8"

if ($ServerOnly) {
    Write-Host "Swagger: http://127.0.0.1:8000/docs" -ForegroundColor Green
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    exit 0
}

$forward = "off"
if (Test-Path ".env") {
    foreach ($line in Get-Content ".env" -Encoding UTF8) {
        if ($line -match '^\s*RENDER_LOG_FORWARD_ENABLED\s*=\s*(.+)$') {
            $v = $Matches[1].Trim().Trim('"').ToLower()
            if ($v -in @("1", "true", "yes")) { $forward = "on" }
        }
    }
}

$target = if ($Render) { "render" } else { "local" }
$cliArgs = @("-m", "app.demo1.run_cli", "--target", $target, "--sample", $Sample, "--source", $Source)
if ($Image) { $cliArgs += @("--image", $Image) }
if ($Audio) { $cliArgs += @("--audio", $Audio) }
if ($Pipeline) { $cliArgs += "--pipeline" }

& .\.venv\Scripts\python.exe @cliArgs

Write-Host "`n[OK] 로컬 결과: output\demo1\ (최신 폴더 또는 render_calls\)" -ForegroundColor Green
Write-Host "  - handoff_*.txt/json, analyze_request.json, final_report.txt (pipeline 시)" -ForegroundColor DarkGray
if ($Render) {
    Write-Host "[OK] Render API 호출 완료 — 응답: output\demo1\render_calls\" -ForegroundColor Green
    if ($forward -eq "on") {
        Write-Host "[OK] 로컬 demo1_log → Render Logs ([forwarded] 검색)" -ForegroundColor Green
    } else {
        Write-Host "[TIP] 로그 모으려면 .env: RENDER_LOG_FORWARD_ENABLED=true + RENDER_SERVICE_URL" -ForegroundColor Yellow
    }
}
