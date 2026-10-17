@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo ============================================
echo  Video-Audio-Converter - Lean Windows build
echo ============================================
echo.

where py >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python launcher "py" was not found.
    echo Install Python 3.10+ and enable the Python launcher.
    pause
    exit /b 1
)

py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,10) else 1)" >nul 2>nul
if errorlevel 1 (
    echo [ERROR] Python 3.10 or newer is required.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo [1/4] Creating local virtual environment...
    py -3 -m venv .venv
    if errorlevel 1 goto :failed
)

echo [2/4] Updating pip...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :failed

echo [3/4] Installing project and build dependencies...
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :failed

echo [4/4] Building with the lean PyInstaller spec...
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean "VideoAudioConverter.spec"
if errorlevel 1 goto :failed

echo.
echo [CLEANUP] Removing temporary build cache and Python bytecode...
if exist "build" rmdir /s /q "build"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ErrorActionPreference='SilentlyContinue'; Get-ChildItem -Path . -Directory -Filter '__pycache__' -Recurse | Remove-Item -Recurse -Force; Get-ChildItem -Path . -File -Filter '*.pyc' -Recurse | Remove-Item -Force"

REM Purge pip download/wheel cache; this does not affect the built EXE.
".venv\Scripts\python.exe" -m pip cache purge >nul 2>nul

REM The virtual environment is not part of the EXE, but can occupy hundreds
REM of MB. Ask before deleting it because the next build must recreate it.
echo.
echo The build environment .venv may occupy several hundred MB.
choice /C YN /N /M "Delete .venv to free disk space? [Y/N] "
if errorlevel 2 goto :keep_venv
if exist ".venv" rmdir /s /q ".venv"
echo [CLEANUP] Removed .venv. The next build will reinstall dependencies.
goto :after_venv
:keep_venv
echo [CLEANUP] Kept .venv so future builds can start faster.
:after_venv


echo.
echo [SUCCESS] Build completed:
echo   %CD%\dist\Converter.exe
echo.
echo This build excludes unused Qt modules and does not bundle FFmpeg.
echo Test Converter.exe on Windows before release.
pause
exit /b 0

:failed
echo.
echo [ERROR] Build failed. Read the error above.
pause
exit /b 1
