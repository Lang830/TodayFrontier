@echo off
rem ==========================================================================
rem  TodayFrontier launcher
rem  Locates a usable pythonw.exe automatically. No hardcoded machine path.
rem ==========================================================================
setlocal

set "ROOT=%~dp0"
set "PYW="

rem ---- 1. project-local virtualenv -----------------------------------------
if exist "%ROOT%.venv\Scripts\pythonw.exe" set "PYW=%ROOT%.venv\Scripts\pythonw.exe"
if not defined PYW if exist "%ROOT%venv\Scripts\pythonw.exe" set "PYW=%ROOT%venv\Scripts\pythonw.exe"

rem ---- 2. pythonw.exe on PATH ----------------------------------------------
if not defined PYW (
    for /f "delims=" %%i in ('where pythonw.exe 2^>nul') do (
        if not defined PYW set "PYW=%%i"
    )
)

if not defined PYW goto :nopython

rem ---- 3. prepend interpreter home to PATH ---------------------------------
rem  A venv's pythonw.exe loads python3xx.dll from its BASE install directory.
rem  Without that entry Windows reports "python313.dll not found" on launch.
for %%i in ("%PYW%") do set "BIN=%%~dpi"
set "BASE="
if exist "%BIN%python.exe" (
    for /f "delims=" %%d in ('"%BIN%python.exe" -c "import sys; print(sys.base_prefix)" 2^>nul') do (
        if not defined BASE set "BASE=%%d"
    )
)
if defined BASE (
    set "PATH=%BASE%;%BIN%;%PATH%"
) else (
    set "PATH=%BIN%;%PATH%"
)

start "" "%PYW%" "%ROOT%src\main.py"
endlocal
exit /b 0

:nopython
echo.
echo   ERROR: pythonw.exe was not found.
echo.
echo   Install the dependencies first:
echo.
echo       pip install -r requirements.txt
echo.
echo   Or create a virtualenv inside the project folder as ".venv"
echo   so this launcher picks it up automatically:
echo.
echo       python -m venv .venv
echo       .venv\Scripts\pip install -r requirements.txt
echo.
pause
exit /b 1
