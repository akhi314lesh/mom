@echo off
setlocal
cd /d "%~dp0"
title MOM for meetings Launcher

echo ==========================================================
echo Starting MOM for meetings...
echo ==========================================================
echo.

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1"

if %ERRORLEVEL% neq 0 (
    echo.
    echo [ERROR] Launcher encountered an error (exit code: %ERRORLEVEL%).
    echo Run .\scripts\doctor.ps1 to diagnose environment issues.
    echo.
    pause
)
