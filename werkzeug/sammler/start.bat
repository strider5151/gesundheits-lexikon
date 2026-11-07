@echo off
chcp 65001 >nul
set PYTHONUTF8=1
cd /d "%~dp0"
title Lexikon-Sammler

where py >nul 2>nul
if errorlevel 1 (
  echo Python wurde nicht gefunden.
  echo Bitte installieren:  winget install Python.Python.3.12
  echo oder von https://www.python.org/downloads/  ^(Haken bei "Add to PATH" setzen^)
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Richte Python-Umgebung ein ^(einmalig^) ...
  py -3 -m venv .venv || (echo Fehler beim Anlegen der Umgebung & pause & exit /b 1)
)
call ".venv\Scripts\activate.bat"
echo Pruefe/aktualisiere Pakete ...
python -m pip install --quiet --upgrade pip
python -m pip install --quiet --upgrade yt-dlp requests beautifulsoup4

python lexikon_sammler.py %*
echo.
pause
