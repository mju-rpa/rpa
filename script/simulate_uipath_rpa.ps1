# UiPath 없이 RPA+Agentic AI 흐름을 터미널로 시연 (백업용)
$ErrorActionPreference = "Stop"
$DemoRoot = Split-Path $PSScriptRoot -Parent
Set-Location $DemoRoot
$env:PYTHONIOENCODING = "utf-8"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  UiPath RPA Simulation (PowerShell)" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

$py = if (Test-Path ".venv\Scripts\python.exe") { ".\.venv\Scripts\python.exe" } else { "python" }

Write-Host "[TASK 1 RPA] Read sample_input.json" -ForegroundColor Yellow
$jsonPath = Join-Path $DemoRoot "input\sample_input.json"
$body = Get-Content $jsonPath -Raw -Encoding UTF8
Write-Host "  -> OK ($($body.Length) bytes)`n" -ForegroundColor Green

Write-Host "[TASK 2 Agentic AI] POST http://localhost:8000/analyze" -ForegroundColor Yellow
try {
    $resp = Invoke-RestMethod -Uri "http://localhost:8000/analyze" -Method Post -Body $body -ContentType "application/json; charset=utf-8"
} catch {
    Write-Host "  API not running. Starting offline pipeline..." -ForegroundColor DarkYellow
    & $py -c @"
from pathlib import Path
import json
from app.consult_alias import register_consult_import_alias
register_consult_import_alias()
from app.workflow.run_pipeline import run_pipeline
from app.agentic_ai.schema.models import AnalyzeRequest
d = json.loads(Path('input/sample_input.json').read_text(encoding='utf-8'))
r = run_pipeline(AnalyzeRequest(**d), Path('output'))
import json as j
print(j.dumps({
    'patient_name': r['analysis']['환자명'],
    'final_score': r['risk_score']['최종점수'],
    'needs_review': r['risk_score']['재검토_필요'],
    'reflection_summary': r.get('reflection_summary',''),
    'agent_trace_summary': r.get('agent_trace_summary',''),
    'report_text': r['report_text'],
}, ensure_ascii=False))
"@
    $resp = $LASTEXITCODE
    exit 0
}

Write-Host "[TASK 2b Agentic AI] Self-Reflection & Score" -ForegroundColor Yellow
Write-Host $resp.reflection_summary
Write-Host "`n=== Risk Score = $($resp.final_score) / 100 ===" -ForegroundColor Magenta
Write-Host $resp.agent_trace_summary

Write-Host "`n[TASK 3 RPA] Save report + branch" -ForegroundColor Yellow
$desktop = [Environment]::GetFolderPath("Desktop")
$outFile = Join-Path $desktop "$($resp.patient_name)_복약리포트.txt"
$resp.report_text | Out-File -FilePath $outFile -Encoding UTF8
Write-Host "  -> Saved: $outFile" -ForegroundColor Green

if ($resp.needs_review) {
    Write-Host "  -> [Message Box] 담당자 재검토 필요 (점수 $($resp.final_score))" -ForegroundColor Red
} else {
    Write-Host "  -> [Message Box] 환자 알림 진행 (데모)" -ForegroundColor Green
}

Write-Host "`n=== DONE (same flow as UiPath Main.xaml) ===`n" -ForegroundColor Cyan
