# Demo2: 팀원 consult OCR/STT API 실연동 (fixture 없음)
# 사전: app/demo2/sample/ 에 pill.jpg, visit.wav (또는 generate_test_media.py)
#       .env 에 GEMINI_API_KEY, TRANSCRIBER_TYPE 등 설정

param(
    [string]$Image = "",
    [string]$Audio = "",
    [switch]$Inprocess,
    [string]$BaseUrl = "",
    [switch]$ServerOnly
)

$ErrorActionPreference = "Stop"
$Root = Split-Path $PSScriptRoot -Parent
Set-Location $Root

Write-Host "`n=== Demo2 (consult POST /ocr/extract + /stt/transcribe) ===" -ForegroundColor Cyan

if (-not (Test-Path ".venv")) { python -m venv .venv }
& .\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
$env:PYTHONIOENCODING = "utf-8"

if ($ServerOnly) {
    Write-Host "1) 이 창: uvicorn 실행" -ForegroundColor Yellow
    Write-Host "2) Swagger POST /demo2/run (image+audio 필수)" -ForegroundColor Green
    & .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
    exit 0
}

$img = if ($Image) { $Image } else { "app\demo2\sample\pill.jpg" }
$aud = if ($Audio) { $Audio } else { "app\demo2\sample\visit.wav" }

if (-not (Test-Path $img)) {
    Write-Host "[ERROR] 이미지 없음: $img" -ForegroundColor Red
    Write-Host "python app/demo2/sample/generate_test_media.py 또는 sample/__init__.py 참고" -ForegroundColor Yellow
    exit 2
}
if (-not (Test-Path $aud)) {
    Write-Host "[ERROR] 음성 없음: $aud" -ForegroundColor Red
    Write-Host "visit.wav: 팀원 녹음 / AI-Hub 샘플 / generate_test_media.py" -ForegroundColor Yellow
    exit 2
}

$args = @("-m", "app.demo2.run_cli", "--image", $img, "--audio", $aud)
if ($Inprocess) { $args += "--inprocess" }
if ($BaseUrl) { $args += @("--base-url", $BaseUrl) }

if (-not $Inprocess -and -not $BaseUrl) {
    Write-Host "[TIP] uvicorn 이 없으면: .\script\run_demo2.ps1 -Inprocess" -ForegroundColor DarkGray
    Write-Host "      또는 터미널1: run_demo2.ps1 -ServerOnly 후 HTTP 모드" -ForegroundColor DarkGray
}

& .\.venv\Scripts\python.exe @args
Write-Host "`n[OK] output\demo2\{timestamp}_consult_api\" -ForegroundColor Green
