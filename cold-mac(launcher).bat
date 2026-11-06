@echo off
where py >nul 2>&1
if %errorlevel%==0 (
    py -3 "%~dp0cold_mac.py" %*
) else (
    python "%~dp0cold_mac.py" %*
)