@echo off
setlocal
cd /d "%~dp0"
title Stop MOM for meetings

powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"

timeout /t 3
