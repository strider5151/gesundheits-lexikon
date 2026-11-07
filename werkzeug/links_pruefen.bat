@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0skripte"
title Lexikon: Links pruefen
where py >nul 2>nul
if errorlevel 1 (
  echo Python wurde nicht gefunden. Bitte installieren:  winget install Python.Python.3.12
  pause & exit /b 1
)
py -3 links_pruefen.py %*
echo.
pause
