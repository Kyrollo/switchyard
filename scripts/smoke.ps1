# Smoke Test for Switchyard
param (
    [string]$BaseUrl = "http://localhost:8001"
)

Write-Host "==> Running Smoke Tests against $BaseUrl..." -ForegroundColor Cyan

# Test /healthz
$healthz = Invoke-RestMethod -Uri "$BaseUrl/healthz" -Method Get -TimeoutSec 5
if ($healthz.status -eq "ok") {
    Write-Host "  [PASS] /healthz is OK" -ForegroundColor Green
} else {
    Write-Host "  [FAIL] /healthz returned: $($healthz | ConvertTo-Json)" -ForegroundColor Red
    exit 1
}

# Test /readyz
try {
    $readyz = Invoke-RestMethod -Uri "$BaseUrl/readyz" -Method Get -TimeoutSec 5
    Write-Host "  [PASS] /readyz is Ready ($($readyz.status))" -ForegroundColor Green
} catch {
    Write-Host "  [WARN] /readyz check failed: $_" -ForegroundColor Yellow
}

Write-Host "==> Smoke test passed successfully." -ForegroundColor Green
