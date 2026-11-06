@echo off
setlocal enabledelayedexpansion

set "SRC=%~dp0"
set "DST=%LOCALAPPDATA%\ColdMac"

net session >nul 2>&1
if %errorlevel%==0 ( set "ADMIN=1" ) else ( set "ADMIN=0" )

if not exist "%DST%" mkdir "%DST%"
for %%F in (cold_mac.py cold-mac.bat uninstall.bat) do (
    copy /Y "%SRC%%%F" "%DST%\%%F" >nul || (echo copy failed: %%F & exit /b 1)
)

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
if "%ADMIN%"=="1" (
    set /p BOOT=Register Cold Mac to re-apply saved MACs at every logon? [y/N]: 
    if /I "!BOOT!"=="y" (
        where py >nul 2>&1
        if errorlevel 1 (
            python "%DST%\cold_mac.py" --boot
        ) else (
            py -3 "%DST%\cold_mac.py" --boot
        )
    )
) else (
    echo note: boot registration needs admin. Re-run install.bat as administrator to enable it.
)

echo.
echo done. open a new terminal and run: cold-mac --list
endlocal