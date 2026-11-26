@echo off
setlocal
cd /d "%~dp0"

if exist "GUR_ArmorEditor.exe" (
    start "" "GUR_ArmorEditor.exe" %*
    exit /b 0
)

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 GUR_ArmorEditor.py %*
    exit /b %errorlevel%
)

where python >nul 2>nul
if %errorlevel%==0 (
    python GUR_ArmorEditor.py %*
    exit /b %errorlevel%
)

echo Python 3 was not found. Put GUR_ArmorEditor.exe next to this file.
pause
