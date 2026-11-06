@echo off
setlocal enabledelayedexpansion

set "SRC=%~dp0"
set "DST=%LOCALAPPDATA%\ColdMac"

if not exist "%DST%" mkdir "%DST%"
copy /Y "%SRC%cold_mac.py" "%DST%\cold_mac.py" >nul || (echo copy failed & exit /b 1)
copy /Y "%SRC%cold-mac.bat" "%DST%\cold-mac.bat" >nul || (echo copy failed & exit /b 1)

for /f "tokens=2*" %%A in ('reg query HKCU\Environment /v PATH 2^>nul') do set "UPATH=%%B"
if defined UPATH (
    echo !UPATH! | find /I "%DST%" >nul
    if errorlevel 1 (
        setx PATH "!UPATH!;%DST%" >nul
        echo added %DST% to user PATH
    ) else (
        echo %DST% already in PATH
    )
) else (
    setx PATH "%DST%" >nul
    echo set user PATH to %DST%
)

echo.
echo done. open a new terminal and run: cold-mac --list
endlocal