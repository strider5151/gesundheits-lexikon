@echo off
cd /d "%~dp0"
rem Geht alle Videos erneut durch, die noch kein Transkript haben, und nutzt Whisper.
call start.bat --nur videos --whisper --neu
