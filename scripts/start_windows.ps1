# AI Commerce Operations Assistant - one-click launcher (Windows)
# Usage (PowerShell, project root):
#   powershell -ExecutionPolicy Bypass -File scripts\start_windows.ps1
# It will:
#   1) create backend/.venv + install requirements if missing
#   2) start the FastAPI backend on http://localhost:8000 (background)
#   3) open the browser at http://localhost:8000

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$backend = Join-Path $root "backend"
$venvPy = Join-Path $backend ".venv\Scripts\python.exe"
$venvUv = Join-Path $backend ".venv\Scripts\uvicorn.exe"
$logOut = Join-Path $backend ".uvicorn.out.log"
$logErr = Join-Path $backend ".uvicorn.err.log"

Write-Host "== AI Commerce Operations Assistant =="
Write-Host "Project root: $root"

# 1) venv + dependencies
if (-not (Test-Path $venvPy)) {
    Write-Host "[1/3] Creating Python venv ..."
    & python -m venv (Join-Path $backend ".venv")
    if (-not (Test-Path $venvPy)) { Write-Error "Failed to create venv. Install Python 3.10+ first." }
    Write-Host "[2/3] Installing requirements (first run may take a while) ..."
    & $venvPy -m pip install --disable-pip-version-check -r (Join-Path $backend "requirements.txt")
    if ($LASTEXITCODE -ne 0) { Write-Error "Core requirements install failed." }
} else {
    Write-Host "[1/3] venv found."
    Write-Host "[2/3] dependencies check done."
}

# optional: transparent cutout (rembg) deps - best effort
$rembgOk = $false
if (Test-Path $venvPy) {
    & $venvPy -c "import rembg, onnxruntime" 2>$null
    if ($LASTEXITCODE -eq 0) { $rembgOk = $true }
}
if (-not $rembgOk) {
    Write-Host "  [optional] installing rembg for transparent cutout (approx 200MB, one-time)..."
    & $venvPy -m pip install --disable-pip-version-check --progress-bar off -r (Join-Path $backend "requirements-segmentation.txt")
    if ($LASTEXITCODE -eq 0) {
        $rembgOk = $true
        Write-Host "  rembg installed -> transparent cutout enabled (model auto-downloads on first use)."
    } else {
        Write-Warning "rembg install failed. Transparent cutout will fall back to the original image. You can retry later: pip install -r backend\requirements-segmentation.txt"
    }
}

# 2) health check on port 8000
function Test-Health {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8000/api/health" -UseBasicParsing -TimeoutSec 2
        return $r.StatusCode -eq 200
    } catch { return $false }
}

if (Test-Health) {
    Write-Host "[3/3] Backend is already running on http://localhost:8000"
    Start-Process "http://localhost:8000"
    exit 0
}

Write-Host "[3/3] Starting backend server ..."
$proc = Start-Process -FilePath $venvUv -ArgumentList "app.main:app --host 127.0.0.1 --port 8000" `
    -WorkingDirectory $backend -WindowStyle Hidden -RedirectStandardOutput $logOut -RedirectStandardError $logErr -PassThru

# wait until healthy (max ~20s)
$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    Start-Sleep -Milliseconds 500
    if (Test-Health) { $ok = $true; break }
}
if ($ok) {
    Write-Host "Backend is up: http://localhost:8000  (pid $($proc.Id))"
    Start-Process "http://localhost:8000"
} else {
    Write-Host "Backend failed to start. Last log lines:"
    if (Test-Path $logOut) { Get-Content $logOut -Tail 20 }
    if (Test-Path $logErr) { Get-Content $logErr -Tail 20 }
    Write-Host "Tip: make sure port 8000 is free and no firewall blocks it."
}
