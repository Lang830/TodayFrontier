@echo off
rem ==========================================================================
rem  TodayFrontier - one-click environment setup
rem  Creates .venv inside the project folder and installs dependencies.
rem  Safe to run repeatedly: already-installed steps are skipped.
rem ==========================================================================
setlocal enabledelayedexpansion

set "ROOT=%~dp0"
cd /d "%ROOT%"

echo.
echo   TodayFrontier - setup
echo   --------------------------------------------------------
echo.

rem ---- 1. locate a base python.exe ----------------------------------------
set "PY="
for /f "delims=" %%i in ('where python.exe 2^>nul') do (
    if not defined PY (
        echo %%i | findstr /i /c:"WindowsApps" >nul || set "PY=%%i"
    )
)

if not defined PY (
    if exist "%LOCALAPPDATA%\Programs\Python" (
        for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do (
            if exist "%%d\python.exe" if not defined PY set "PY=%%d\python.exe"
        )
    )
)
if not defined PY if exist "C:\Python313\python.exe" set "PY=C:\Python313\python.exe"
if not defined PY if exist "C:\Python312\python.exe" set "PY=C:\Python312\python.exe"
if not defined PY if exist "C:\Python311\python.exe" set "PY=C:\Python311\python.exe"

if not defined PY goto :nopython
echo   [1/3] python   : %PY%

rem ---- 2. create virtualenv ------------------------------------------------
if exist "%ROOT%.venv\Scripts\python.exe" (
    echo   [2/3] venv     : already exists, skipped
) else (
    echo   [2/3] venv     : creating .venv ...
    "%PY%" -m venv "%ROOT%.venv"
    if errorlevel 1 goto :venvfail
)

set "VPY=%ROOT%.venv\Scripts\python.exe"
set "VPIP=%ROOT%.venv\Scripts\pip.exe"
if not exist "%VPIP%" goto :venvfail

rem ---- 3. install dependencies ---------------------------------------------
echo   [3/3] deps     : installing PySide6-Essentials (about 80 MB) ...
echo.
"%VPIP%" install -r "%ROOT%requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --disable-pip-version-check --no-input
if errorlevel 1 (
    echo.
    echo   Mirror failed, retrying with the official index ...
    "%VPIP%" install -r "%ROOT%requirements.txt" --disable-pip-version-check --no-input
    if errorlevel 1 goto :pipfail
)

echo.
echo   --------------------------------------------------------
echo   Setup complete.
echo.
set /p "RUN=   Launch TodayFrontier now? [Y/n] "
if /i "!RUN!"=="n" goto :done
start "" "%ROOT%.venv\Scripts\pythonw.exe" "%ROOT%src\main.py"
goto :done

:nopython
echo   ERROR: Python was not found on this machine.
echo.
echo   Install Python 3.11 or newer from https://www.python.org/downloads/
echo   and tick "Add python.exe to PATH" during installation.
echo   Then run this script again.
echo.
pause
exit /b 1

:venvfail
echo   ERROR: failed to create the virtual environment.
echo   Make sure Python was installed with the "venv" component enabled.
echo.
pause
exit /b 1

:pipfail
echo.
echo   ERROR: failed to install dependencies.
echo   Check your network connection, then run this script again.
echo.
pause
exit /b 1

:done
endlocal
exit /b 0
