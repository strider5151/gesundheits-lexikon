@echo off
chcp 65001 >nul
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Bitte zuerst einmal start.bat ausfuehren.
  pause
  exit /b 1
)
call ".venv\Scripts\activate.bat"
echo Installiere faster-whisper ^(Spracherkennung, ca. 200 MB^) ...
python -m pip install --upgrade faster-whisper
echo.
echo Fertig. Jetzt "nur_fehlende_transkripte.bat" starten.
pause
