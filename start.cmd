@echo off
setlocal
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0projectSkill\launcher.ps1" -Action start -ProjectRoot "%~dp0"
set "exit_code=%ERRORLEVEL%"
if not defined PAPER_LAUNCHER_NO_PAUSE pause
exit /b %exit_code%
