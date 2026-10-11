# Development Launcher for Switchyard
Write-Host "==> Starting Switchyard Development Environment..." -ForegroundColor Cyan

# 1. Check Python and dependencies
Write-Host "--> Checking backend on port 8001..." -ForegroundColor Yellow
$backendJob = Start-Job -ScriptBlock {
    Set-Location "$using:PWD\backend"
    python -m uvicorn src.switchyard.main:app --host 0.0.0.0 --port 8001 --reload
}

# 2. Check Frontend
Write-Host "--> Checking frontend on port 3001..." -ForegroundColor Yellow
$frontendJob = Start-Job -ScriptBlock {
    Set-Location "$using:PWD\frontend"
    npm run dev -- --port 3001
}

Write-Host "Services started! Press Ctrl+C to terminate." -ForegroundColor Green
Receive-Job -Job $backendJob, $frontendJob -Wait
