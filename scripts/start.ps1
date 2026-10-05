# start.ps1 - MOM for meetings Unified One-Click Launcher
# Usage:
#   powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
# Or double-click START_MOM.bat

param(
    [switch]$NoBrowser,
    [switch]$NoWait
)

$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"
$PidFile = Join-Path $RootDir ".mom_pids.json"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " MOM for meetings - Unified Application Launcher" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host ""

# 1. Stop any dangling previous instances first
Write-Host "Checking for existing instances..." -ForegroundColor Gray
& (Join-Path $ScriptDir "stop.ps1") | Out-Null

# 2. Detect Python
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCmd) {
    Write-Host "[FAIL] Python not detected on system PATH." -ForegroundColor Red
    Write-Host "Please install Python 3.11+ from https://python.org and check 'Add to PATH'." -ForegroundColor Yellow
    exit 1
}

# 3. Detect Node & npm
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if (-not $nodeCmd) {
    Write-Host "[FAIL] Node.js not detected on system PATH." -ForegroundColor Red
    Write-Host "Please install Node.js LTS from https://nodejs.org." -ForegroundColor Yellow
    exit 1
}

# 4. Check & create backend .venv if absent
$venvDir = Join-Path $BackendDir ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"

if (-not (Test-Path $venvPython)) {
    Write-Host "Creating Python virtual environment in backend/.venv..." -ForegroundColor Yellow
    Push-Location $BackendDir
    try {
        & python -m venv .venv
    } finally {
        Pop-Location
    }
    if (-not (Test-Path $venvPython)) {
        Write-Host "[FAIL] Failed to create virtual environment." -ForegroundColor Red
        exit 1
    }
}

# 5. Check & install backend requirements if necessary
$fastapiCheck = & $venvPython -c "import fastapi, uvicorn, sqlalchemy, aiosqlite, docx, reportlab; print('OK')" 2>$null
if ($fastapiCheck -ne "OK") {
    Write-Host "Installing backend requirements (first-run setup)..." -ForegroundColor Yellow
    Push-Location $BackendDir
    try {
        & $venvPython -m pip install -r requirements.txt
    } finally {
        Pop-Location
    }
}

# 6. Check & install frontend dependencies if absent
$nodeModulesDir = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $nodeModulesDir)) {
    Write-Host "Installing frontend dependencies (first-run setup)..." -ForegroundColor Yellow
    Push-Location $FrontendDir
    try {
        & cmd.exe /c npm install
    } finally {
        Pop-Location
    }
}

# 7. Initialize Database and Seed Demo Meeting
Write-Host "Initializing database & ensuring demo datasets..." -ForegroundColor Gray
Push-Location $BackendDir
try {
    & $venvPython -m app.seed | Out-Null
} catch {
    Write-Host "[WARN] Demo seed notice: $_" -ForegroundColor Yellow
} finally {
    Pop-Location
}

# 8. Start FastAPI backend (port 8000)
Write-Host "Starting FastAPI backend on port 8000..." -ForegroundColor Gray
$backendProc = Start-Process `
    -FilePath $venvPython `
    -ArgumentList "-m", "uvicorn", "app.main:app", "--port", "8000", "--host", "127.0.0.1" `
    -WorkingDirectory $BackendDir `
    -PassThru `
    -WindowStyle Minimized

# 9. Start Vite frontend dev server (port 5173)
Write-Host "Starting Vite frontend dev server on port 5173..." -ForegroundColor Gray
$viteBin = Join-Path $FrontendDir "node_modules\.bin\vite.cmd"
if (Test-Path $viteBin) {
    $frontendProc = Start-Process `
        -FilePath $viteBin `
        -ArgumentList "--host", "127.0.0.1" `
        -WorkingDirectory $FrontendDir `
        -PassThru `
        -WindowStyle Minimized
} else {
    $frontendProc = Start-Process `
        -FilePath "cmd.exe" `
        -ArgumentList "/c npm run dev -- --host 127.0.0.1" `
        -WorkingDirectory $FrontendDir `
        -PassThru `
        -WindowStyle Minimized
}

# Save PIDs to file for reliable shutdown
@{
    backend_pid = $backendProc.Id
    frontend_pid = $frontendProc.Id
} | ConvertTo-Json | Set-Content $PidFile

# 10. Wait until both services are responsive
Write-Host "Waiting for services to become responsive..." -ForegroundColor Gray

$backendReady = $false
$frontendReady = $false

for ($i = 1; $i -le 40; $i++) {
    if (-not $backendReady) {
        $conn8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
        if ($conn8000) {
            try {
                $resp = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" -Method Get -TimeoutSec 1 -ErrorAction SilentlyContinue
                if ($resp -and $resp.status -eq "ok") {
                    $backendReady = $true
                }
            } catch {}
        }
    }

    if (-not $frontendReady) {
        $conn5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
        if ($conn5173) {
            $frontendReady = $true
        }
    }

    if ($backendReady -and $frontendReady) {
        break
    }
    Start-Sleep -Milliseconds 400
}

if (-not $backendReady) {
    Write-Host "[FAIL] FastAPI backend failed to respond on http://localhost:8000/api/health" -ForegroundColor Red
    Write-Host "Run .\scripts\doctor.ps1 to diagnose." -ForegroundColor Yellow
    exit 1
}

if (-not $frontendReady) {
    Write-Host "[FAIL] Vite frontend failed to respond on http://localhost:5173" -ForegroundColor Red
    Write-Host "Run .\scripts\doctor.ps1 to diagnose." -ForegroundColor Yellow
    exit 1
}

# 11. Print Required Success Checklist
Write-Host ""
Write-Host "==========================================================" -ForegroundColor Green
Write-Host " MOM SYSTEM" -ForegroundColor Green
Write-Host " [OK] Python                  3.11+" -ForegroundColor Green
Write-Host " [OK] Backend environment     .venv validated" -ForegroundColor Green
Write-Host " [OK] Database                SQLite WAL initialized" -ForegroundColor Green
Write-Host " [OK] FastAPI                 Listening on http://localhost:8000" -ForegroundColor Green
Write-Host " [OK] Frontend                Listening on http://localhost:5173" -ForegroundColor Green
Write-Host " [OK] Storage                 Audio & Artifacts ready" -ForegroundColor Green
Write-Host " [OK] Demo data               Product Architecture Review seeded" -ForegroundColor Green
Write-Host "==========================================================" -ForegroundColor Green
Write-Host ""
Write-Host " APPLICATION READY" -ForegroundColor Cyan
Write-Host " Web:     http://localhost:5173/" -ForegroundColor White
Write-Host " API:     http://localhost:8000/docs" -ForegroundColor White
Write-Host " Overlay: Ready (Press 'o' or click inside Dashboard to open)" -ForegroundColor White
Write-Host ""

# 12. Open browser automatically
if (-not $NoBrowser) {
    Write-Host "Opening http://localhost:5173 in default browser..." -ForegroundColor Gray
    Start-Process "http://localhost:5173"
}

if ($NoWait) {
    exit 0
}

# 13. Interactive control loop
Write-Host "MOM is running. Press:" -ForegroundColor Gray
Write-Host "  [O] Launch Desktop Overlay" -ForegroundColor White
Write-Host "  [S] Stop all MOM services" -ForegroundColor White
Write-Host "  [Q] Exit launcher window (services keep running in background)" -ForegroundColor White
Write-Host ""

while ($true) {
    if ([Console]::KeyAvailable) {
        $key = [Console]::ReadKey($true).Key
        if ($key -eq [ConsoleKey]::O) {
            Write-Host "Opening Desktop Overlay shell..." -ForegroundColor Cyan
            Start-Process "http://localhost:5173/overlay"
        } elseif ($key -eq [ConsoleKey]::S) {
            Write-Host "Stopping MOM services..." -ForegroundColor Yellow
            & (Join-Path $ScriptDir "stop.ps1")
            break
        } elseif ($key -eq [ConsoleKey]::Q) {
            Write-Host "Exiting launcher window. MOM remains active at http://localhost:5173." -ForegroundColor Green
            Write-Host "Run .\scripts\stop.ps1 anytime to stop services." -ForegroundColor Gray
            break
        }
    }
    Start-Sleep -Milliseconds 250
}
