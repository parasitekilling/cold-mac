@echo off
setlocal
chcp 65001 >nul

where py >nul 2>&1
if errorlevel 1 (
    echo Python launcher not found.
    echo Install Python 3.10 or newer, including the Windows py launcher.
    pause
    exit /b 1
)

py -3 "%~dp0cold_mac.py" %*
set "RESULT=%ERRORLEVEL%"

if not "%RESULT%"=="0" (
    echo.
    echo Cold Mac exited with status %RESULT%.
    pause
)

exit /b %RESULT%