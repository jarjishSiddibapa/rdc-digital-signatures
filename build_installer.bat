@echo off
setlocal enabledelayedexpansion
echo.
echo ================================================================
echo   RDC Digital Signatures - Complete Build Pipeline
echo   Builds standalone EXE + Windows Installer (Setup.exe)
echo   Last updated: 2026-02-10
echo ================================================================
echo.

REM ===== CONFIGURATION =====
set "VENV_DIR=venv"
set "SPEC_FILE=RDCSignatures.spec"
set "ISS_FILE=installer.iss"
set "INNO_COMPILER=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "DIST_DIR=dist\RDCSignatures"
set "INSTALLER_OUTPUT=installer_output"

REM ===== STEP 1: Activate Virtual Environment =====
echo [1/5] Activating virtual environment...
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at %VENV_DIR%
    echo Please create it first: python -m venv venv
    pause
    exit /b 1
)
call %VENV_DIR%\Scripts\activate.bat
echo       Done.
echo.

REM ===== STEP 2: Install/Update PyInstaller =====
echo [2/5] Ensuring PyInstaller is installed...
pip install pyinstaller --quiet --upgrade
if errorlevel 1 (
    echo ERROR: Failed to install PyInstaller
    pause
    exit /b 1
)
echo       Done.
echo.

REM ===== STEP 3: Clean Previous Build =====
echo [3/5] Cleaning previous build artifacts...
if exist "build" rmdir /s /q "build" 2>nul
if exist "%DIST_DIR%" rmdir /s /q "%DIST_DIR%" 2>nul
echo       Done.
echo.

REM ===== STEP 4: Build with PyInstaller =====
echo [4/5] Building standalone application with PyInstaller...
echo       This may take 2-5 minutes...
echo.
pyinstaller --clean --noconfirm "%SPEC_FILE%"
if errorlevel 1 (
    echo.
    echo ================================================================
    echo   ERROR: PyInstaller build FAILED!
    echo   Check the output above for details.
    echo ================================================================
    pause
    exit /b 1
)
echo.
echo       PyInstaller build SUCCEEDED!
echo.

REM ===== Verify dist output =====
if not exist "%DIST_DIR%\RDCSignatures.exe" (
    echo ERROR: RDCSignatures.exe not found in %DIST_DIR%
    echo Build may have failed silently.
    pause
    exit /b 1
)
echo       Verified: RDCSignatures.exe exists in %DIST_DIR%
echo.

REM ===== STEP 5: Build Installer with Inno Setup =====
echo [5/5] Building Windows Installer with Inno Setup...
if not exist "%INNO_COMPILER%" (
    echo.
    echo WARNING: Inno Setup not found at:
    echo   "%INNO_COMPILER%"
    echo.
    echo PyInstaller build is complete. You can:
    echo   1. Run the app directly from: %DIST_DIR%\RDCSignatures.exe
    echo   2. Install Inno Setup 6 from: https://jrsoftware.org/isinfo.php
    echo   3. Then open %ISS_FILE% and compile manually.
    echo.
    pause
    exit /b 0
)

if not exist "%INSTALLER_OUTPUT%" mkdir "%INSTALLER_OUTPUT%"

"%INNO_COMPILER%" "%ISS_FILE%"
if errorlevel 1 (
    echo.
    echo ================================================================
    echo   ERROR: Inno Setup compilation FAILED!
    echo   Check the output above for details.
    echo ================================================================
    pause
    exit /b 1
)

echo.
echo ================================================================
echo   BUILD COMPLETE - ALL STEPS SUCCEEDED!
echo ================================================================
echo.
echo   Standalone App:  %DIST_DIR%\RDCSignatures.exe
echo   Windows Installer: %INSTALLER_OUTPUT%\RDCSignatures_Setup_v1.0.0.exe
echo.
echo   IMPORTANT: The installer installs the app to Program Files.
echo   User data (database + signed output) is stored per-user in:
echo     %%LOCALAPPDATA%%\RDCSignatures\
echo   This is fully writable without admin rights.
echo.
echo ================================================================
pause
