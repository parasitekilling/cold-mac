@echo off
setlocal enabledelayedexpansion
set "DST=%LOCALAPPDATA%\ColdMac"

if exist "%DST%\cold_mac.py" (
    where py >nul 2>&1
    if errorlevel 1 ( set "PY=python" ) else ( set "PY=py -3" )
    %PY% "%DST%\cold_mac.py" --no-boot >nul 2>&1
    %PY% "%DST%\cold_mac.py" --restore-all
)

for /f "tokens=2*" %%A in ('reg query HKCU\Environment /v PATH 2^>nul') do set "UPATH=%%B"
if defined UPATH (
    set "NEWPATH=!UPATH:;%DST%=!"
    set "NEWPATH=!NEWPATH:%DST%=!"
    if not "!NEWPATH!"=="!UPATH!" (
        setx PATH "!NEWPATH!" >nul
        echo removed %DST% from user PATH
    )
)

if exist "%DST%" rmdir /S /Q "%DST%"
echo done.
endlocal