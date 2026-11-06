@echo off
where py >nul 2>&1
if errorlevel 1 (
    python "%~dp0cold_mac.py" %*
) else (
    py -3 "%~dp0cold_mac.py" %*
)