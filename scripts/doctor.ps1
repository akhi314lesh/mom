# doctor.ps1 - MOM for meetings Operational Diagnostic Utility

param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $RootDir "backend"
$FrontendDir = Join-Path $RootDir "frontend"

$passCount = 0
$warnCount = 0
$failCount = 0

function Print-Header {
    Write-Host ""
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host " MOM for meetings -- Operational Doctor and Diagnostics" -ForegroundColor Cyan
    Write-Host " Target Directory: $RootDir" -ForegroundColor Gray
    Write-Host "==========================================================" -ForegroundColor Cyan
    Write-Host ""
}

function Report-Pass {
    param([string]$Category, [string]$Message)
    $script:passCount++
    Write-Host " [PASS] " -ForegroundColor Green -NoNewline
    Write-Host ("{0,-18}: " -f $Category) -ForegroundColor White -NoNewline
    Write-Host $Message -ForegroundColor Gray
}

function Report-Warn {
    param([string]$Category, [string]$Message, [string]$Fix)
    $script:warnCount++
    Write-Host " [WARN] " -ForegroundColor Yellow -NoNewline
    Write-Host ("{0,-18}: " -f $Category) -ForegroundColor White -NoNewline
    Write-Host $Message -ForegroundColor Yellow
    if ($Fix) {
        Write-Host "        Suggested Fix  : $Fix" -ForegroundColor DarkYellow
    }
}

function Report-Fail {
    param([string]$Category, [string]$Message, [string]$Fix)
    $script:failCount++
    Write-Host " [FAIL] " -ForegroundColor Red -NoNewline
    Write-Host ("{0,-18}: " -f $Category) -ForegroundColor White -NoNewline
    Write-Host $Message -ForegroundColor Red
    if ($Fix) {
        Write-Host "        Actionable Fix : $Fix" -ForegroundColor DarkRed
    }
}

Print-Header

# 1. Python System Detection
$pythonCmd = Get-Command python -ErrorAction SilentlyContinue
if ($pythonCmd) {
    try {
        $pyVersion = (& python --version 2>&1).ToString().Trim()
        Report-Pass "Python" "$pyVersion detected at $($pythonCmd.Source)"
    } catch {
        Report-Fail "Python" "Python command found but failed to execute." "Ensure Python is accessible in system PATH."
    }
} else {
    Report-Fail "Python" "Python is not installed or not in system PATH." "Install Python 3.11+ from https://python.org and check 'Add to PATH'."
}

# 2. Node and npm Detection
$nodeCmd = Get-Command node -ErrorAction SilentlyContinue
if ($nodeCmd) {
    try {
        $nodeVersion = (& node --version 2>&1).ToString().Trim()
        Report-Pass "Node.js" "$nodeVersion detected at $($nodeCmd.Source)"
    } catch {
        Report-Fail "Node.js" "Node command found but failed to execute." "Reinstall Node.js LTS from https://nodejs.org."
    }
} else {
    Report-Fail "Node.js" "Node.js is not installed or not in system PATH." "Install Node.js 18+ from https://nodejs.org."
}

$npmCmd = Get-Command npm -ErrorAction SilentlyContinue
if ($npmCmd) {
    try {
        $npmVersion = (& npm --version 2>&1).ToString().Trim()
        Report-Pass "npm" "v$npmVersion detected at $($npmCmd.Source)"
    } catch {
        Report-Fail "npm" "npm command found but failed to execute." "Ensure npm is installed alongside Node.js."
    }
} else {
    Report-Fail "npm" "npm is not installed." "Install Node.js LTS which includes npm."
}

# 3. Backend Virtual Environment (.venv)
$venvPython = Join-Path $BackendDir ".venv\Scripts\python.exe"
if (Test-Path $venvPython) {
    Report-Pass "Backend venv" "Virtualenv located at backend/.venv"
} else {
    Report-Fail "Backend venv" "Virtual environment (.venv) not found in backend directory." "Run: cd backend; python -m venv .venv; .\.venv\Scripts\pip install -r requirements.txt"
}

# 4. Critical Python Packages
if (Test-Path $venvPython) {
    $requiredPackages = @("fastapi", "uvicorn", "sqlalchemy", "aiosqlite", "docx", "reportlab", "pydantic_settings")
    $missingPackages = @()
    foreach ($pkg in $requiredPackages) {
        $pkgCheck = & $venvPython -c "import $pkg; print('OK')" 2>$null
        if ($pkgCheck -ne "OK") {
            $missingPackages += $pkg
        }
    }
    if ($missingPackages.Count -eq 0) {
        Report-Pass "Python Packages" "All core dependencies verified (FastAPI, SQLAlchemy, Docx, ReportLab, etc.)"
    } else {
        $joined = $missingPackages -join ", "
        Report-Fail "Python Packages" "Missing required Python packages: $joined" "Run: backend\.venv\Scripts\pip.exe install -r backend\requirements.txt"
    }
}

# 5. Frontend Node Modules
$nodeModulesDir = Join-Path $FrontendDir "node_modules"
if (Test-Path $nodeModulesDir) {
    Report-Pass "Frontend Modules" "node_modules directory found in frontend/"
} else {
    Report-Fail "Frontend Modules" "frontend/node_modules directory is missing." "Run: cd frontend; npm install"
}

# 6. Database and Storage Paths
$dbFile = Join-Path $BackendDir "meeting_intelligence.db"
if (Test-Path $dbFile) {
    $dbSize = (Get-Item $dbFile).Length
    Report-Pass "Database" "SQLite database file exists ($dbSize bytes)"
} else {
    Report-Warn "Database" "meeting_intelligence.db not found (will be auto-created on initial start)." "Running start.ps1 will automatically create and initialize the database."
}

$storageDir = Join-Path $BackendDir "storage"
$artifactsDir = Join-Path $storageDir "artifacts"
$audioDir = Join-Path $storageDir "audio"
if ((Test-Path $artifactsDir) -and (Test-Path $audioDir)) {
    Report-Pass "Storage Paths" "Storage directories verified at backend/storage (audio, artifacts)"
} else {
    Report-Warn "Storage Paths" "Storage directories not fully created yet." "Will be auto-created on application startup."
}

# 7. Port Availability (8000 and 5173)
$port8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($port8000) {
    $pId = $port8000.OwningProcess[0]
    $proc = Get-Process -Id $pId -ErrorAction SilentlyContinue
    Report-Warn "Port 8000 (API)" "Port 8000 is currently occupied by PID $pId ($($proc.ProcessName))." "If this is an old MOM backend instance, run scripts/stop.ps1."
} else {
    Report-Pass "Port 8000 (API)" "Port 8000 is free and available for FastAPI."
}

$port5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($port5173) {
    $pId = $port5173.OwningProcess[0]
    $proc = Get-Process -Id $pId -ErrorAction SilentlyContinue
    Report-Warn "Port 5173 (Web)" "Port 5173 is currently occupied by PID $pId ($($proc.ProcessName))." "If this is an old Vite instance, run scripts/stop.ps1."
} else {
    Report-Pass "Port 5173 (Web)" "Port 5173 is free and available for Vite dev server."
}

# 8. FastAPI Import Integrity
if (Test-Path $venvPython) {
    Push-Location $BackendDir
    try {
        $importCheck = & $venvPython -c "from app.main import app; print('FASTAPI_IMPORT_OK')" 2>&1
        if ($importCheck -match "FASTAPI_IMPORT_OK") {
            Report-Pass "FastAPI Import" "FastAPI application imports successfully with all routers registered."
        } else {
            Report-Fail "FastAPI Import" "Failed to import app.main: $importCheck" "Inspect backend error logs or reinstall dependencies."
        }
    } finally {
        Pop-Location
    }
}

# 9. Provider Configuration and Zero-Key Validation
if (Test-Path $venvPython) {
    Push-Location $BackendDir
    try {
        $configCheck = & $venvPython -c "from app.config import settings; print(f'{settings.llm_provider}|{settings.asr_provider}|{settings.diarization_provider}')" 2>$null
        if ($configCheck) {
            $parts = $configCheck.Trim().Split('|')
            Report-Pass "AI Providers" "LLM: $($parts[0]), ASR: $($parts[1]), Diarization: $($parts[2]) (Zero-key DEMO mode supported)"
        }
    } finally {
        Pop-Location
    }
}

# Summary
Write-Host ""
Write-Host "----------------------------------------------------------" -ForegroundColor Gray
Write-Host " Diagnostic Summary: " -NoNewline -ForegroundColor White
Write-Host "$script:passCount Passed  " -ForegroundColor Green -NoNewline
Write-Host "$script:warnCount Warnings  " -ForegroundColor Yellow -NoNewline
Write-Host "$script:failCount Failures" -ForegroundColor Red
Write-Host "----------------------------------------------------------" -ForegroundColor Gray

if ($script:failCount -eq 0) {
    Write-Host " Status: READY TO LAUNCH" -ForegroundColor Green
    Write-Host " Run .\scripts\start.ps1 or double-click START_MOM.bat" -ForegroundColor White
    exit 0
} else {
    Write-Host " Status: REMEDIATION REQUIRED BEFORE LAUNCH" -ForegroundColor Red
    Write-Host " Review the actionable fixes listed above." -ForegroundColor White
    exit 1
}
