@echo off
rem ==========================================================================
rem  TodayFrontier - build a standalone Windows executable
rem  Requires: .venv with PySide6 + PyInstaller installed (run install.bat first,
rem            then: .venv\Scripts\pip install pyinstaller)
rem  Output  : dist\TodayFrontier\TodayFrontier.exe
rem ==========================================================================
setlocal

set "ROOT=%~dp0"
cd /d "%ROOT%"

if not exist "%ROOT%.venv\Scripts\python.exe" (
    echo   ERROR: .venv not found. Run install.bat first.
    pause
    exit /b 1
)

set "VPY=%ROOT%.venv\Scripts\python.exe"

"%VPY%" -c "import PyInstaller" 2>nul
if errorlevel 1 (
    echo   Installing PyInstaller ...
    "%ROOT%.venv\Scripts\pip.exe" install pyinstaller --disable-pip-version-check --no-input
    if errorlevel 1 (
        echo   ERROR: failed to install PyInstaller.
        pause
        exit /b 1
    )
)

echo.
echo   Building ... this takes 1-3 minutes.
echo.

"%VPY%" -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --windowed ^
    --onedir ^
    --name TodayFrontier ^
    --paths "%ROOT%src" ^
    --add-data "%ROOT%resources;resources" ^
    --distpath "%ROOT%dist" ^
    --workpath "%ROOT%build" ^
    --specpath "%ROOT%build" ^
    "%ROOT%src\main.py"

if errorlevel 1 (
    echo.
    echo   ERROR: build failed. See the output above.
    pause
    exit /b 1
)

echo.
echo   --------------------------------------------------------
echo   Done: dist\TodayFrontier\TodayFrontier.exe
echo   Zip the whole dist\TodayFrontier folder to share it.
echo   --------------------------------------------------------
echo.
pause
endlocal
exit /b 0
