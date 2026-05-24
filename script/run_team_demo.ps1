# 팀 데모: 로컬 FastAPI + (선택) Render Logs 전송 + 리포트 확인
# 사용: .\script\run_team_demo.ps1
# 사전: cp .env.example .env 후 RENDER_* 설정 (dev_doc/logging-render.md)

$ErrorActionPreference = "Stop"
$DemoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $DemoRoot

Write-Host "`n=== Atlas Medical Team Demo (local PC) ===" -ForegroundColor Cyan

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "[ERROR] Python not found. Install Python 3.10+" -ForegroundColor Red
    exit 1
}

if (-not (Test-Path ".env")) {
    Write-Host "[WARN] .env 없음 — cp .env.example .env 후 RENDER_LOG_FORWARD_ENABLED=true 권장" -ForegroundColor Yellow
}

$env:PYTHONIOENCODING = "utf-8"
if (-not (Test-Path ".venv")) {
    python -m venv .venv
}
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt

$forward = "off"
if (Test-Path ".env") {
    foreach ($line in Get-Content ".env" -Encoding UTF8) {
        if ($line -match '^\s*RENDER_LOG_FORWARD_ENABLED\s*=\s*(.+)$') {
            $v = $Matches[1].Trim().Trim('"').ToLower()
            if ($v -in @("1", "true", "yes")) { $forward = "on" }
        }
    }
}
Write-Host "Render log forward: $forward (Render 대시보드 Logs에서 [forwarded] 검색)" -ForegroundColor DarkGray

$port = 8000
$base = "http://127.0.0.1:$port"
$uvicorn = Start-Process -FilePath ".\.venv\Scripts\python.exe" `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", $port `
    -PassThru -WindowStyle Hidden

function Invoke-Pipeline($sample) {
    return Invoke-RestMethod -Method Post -Uri "$base/demo/pipeline?sample=$sample"
}

try {
    Start-Sleep -Seconds 4
    Write-Host "[1/2] POST /demo/pipeline?sample=normal" -ForegroundColor Yellow
    $r1 = Invoke-Pipeline "normal"
    Write-Host "[2/2] POST /demo/pipeline?sample=high_risk (HIDL)" -ForegroundColor Magenta
    $r2 = Invoke-Pipeline "high_risk"

    function Show-Report($label, $r) {
        $name = $r.patient_name
        if (-not $name -and $r.analysis) { $name = $r.analysis.'환자명' }
        Write-Host "`n--- $label | $($r.workflow_stage) | $name ---" -ForegroundColor Green
        if ($r.report_file) { Write-Host "report_file: $($r.report_file)" }
        if ($r.report_text) {
            $preview = ($r.report_text -split "`n" | Select-Object -First 8) -join "`n"
            Write-Host $preview
            Write-Host "... (전체는 output\ 또는 Swagger report_text)" -ForegroundColor DarkGray
        }
    }
    Show-Report "normal" $r1
    Show-Report "high_risk" $r2

    Write-Host "`n[OK] 로컬 Swagger: $base/docs" -ForegroundColor Green
    if ($forward -eq "on") {
        Write-Host "[OK] Render Logs: https://dashboard.render.com → mju-rpa → Logs → 'forwarded' 또는 'step='" -ForegroundColor Green
    } else {
        Write-Host "[TIP] Render에 로그 모으려면 .env 에 RENDER_SERVICE_URL + RENDER_LOG_FORWARD_ENABLED=true" -ForegroundColor Yellow
    }
    Write-Host ""
} finally {
    Stop-Process -Id $uvicorn.Id -Force -ErrorAction SilentlyContinue
}
