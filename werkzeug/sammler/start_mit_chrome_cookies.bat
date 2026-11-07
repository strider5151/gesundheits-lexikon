@echo off
cd /d "%~dp0"
echo Bitte vorher Chrome komplett schliessen!
echo.
call start.bat --cookies chrome
