# stop.ps1 - Gracefully terminate all MOM for meetings services

param()

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$RootDir = Split-Path -Parent $ScriptDir
$PidFile = Join-Path $RootDir ".mom_pids.json"

Write-Host ""
Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Stopping MOM for meetings services..." -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

$killedCount = 0

# 1. Kill tracked PIDs from .mom_pids.json if present
if (Test-Path $PidFile) {
    try {
        $pidsJson = Get-Content $PidFile -Raw | ConvertFrom-Json
        if ($pidsJson.backend_pid) {
            $p = Get-Process -Id $pidsJson.backend_pid -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host " Stopping tracked backend process (PID $($p.Id))..." -ForegroundColor Yellow
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                $killedCount++
            }
        }
        if ($pidsJson.frontend_pid) {
            $p = Get-Process -Id $pidsJson.frontend_pid -ErrorAction SilentlyContinue
            if ($p) {
                Write-Host " Stopping tracked frontend process (PID $($p.Id))..." -ForegroundColor Yellow
                Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue
                $killedCount++
            }
        }
        Remove-Item $PidFile -Force -ErrorAction SilentlyContinue
    } catch {}
}

# 2. Free port 8000 (FastAPI / uvicorn)
$conn8000 = Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue
if ($conn8000) {
    foreach ($conn in $conn8000) {
        $pidToKill = $conn.OwningProcess
        if ($pidToKill -gt 4) {
            $proc = Get-Process -Id $pidToKill -ErrorAction SilentlyContinue
            Write-Host " Terminating process on port 8000: PID $pidToKill ($($proc.ProcessName))..." -ForegroundColor Yellow
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            $killedCount++
        }
    }
}

# 3. Free port 5173 (Vite / Node)
$conn5173 = Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue
if ($conn5173) {
    foreach ($conn in $conn5173) {
        $pidToKill = $conn.OwningProcess
        if ($pidToKill -gt 4) {
            $proc = Get-Process -Id $pidToKill -ErrorAction SilentlyContinue
            Write-Host " Terminating process on port 5173: PID $pidToKill ($($proc.ProcessName))..." -ForegroundColor Yellow
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            $killedCount++
        }
    }
}

# 4. Free port 8001 (Overlay companion if running)
$conn8001 = Get-NetTCPConnection -LocalPort 8001 -State Listen -ErrorAction SilentlyContinue
if ($conn8001) {
    foreach ($conn in $conn8001) {
        $pidToKill = $conn.OwningProcess
        if ($pidToKill -gt 4) {
            $proc = Get-Process -Id $pidToKill -ErrorAction SilentlyContinue
            Write-Host " Terminating overlay companion process on port 8001: PID $pidToKill..." -ForegroundColor Yellow
            Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            $killedCount++
        }
    }
}

Start-Sleep -Milliseconds 600

Write-Host ""
if ($killedCount -gt 0) {
    Write-Host " [OK] Terminated $killedCount process(es). Ports 8000 and 5173 are now free." -ForegroundColor Green
} else {
    Write-Host " [OK] No running MOM processes detected on ports 8000, 5173, or 8001." -ForegroundColor Green
}
Write-Host ""
