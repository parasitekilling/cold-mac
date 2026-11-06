@echo off
where py >nul 2>&1
if errorlevel 1 (
    set "PY=python"
) else (
    set "PY=py -3"
)

if "%~1"=="" (
    %PY% "%~dp0cold_mac.py" --help
    echo.
    echo Run from a terminal with arguments, e.g.:
    echo     py -3 cold_mac.py --list
    echo     py -3 cold_mac.py -i "WiFi 2" --random --vendor Realtek
    pause
    exit /b 1
)

%PY% "%~dp0cold_mac.py" %*