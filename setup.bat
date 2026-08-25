@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ============================================================
echo    Miss Universe Nail Art Studio  -  one-time setup
echo ============================================================
echo.

REM --- 1) Locate a Python 3 launcher -------------------------------------
set "PYEXE="
for %%P in ("py -3.13" "py -3" "python") do (
  if not defined PYEXE (
    %%~P -c "import sys" >nul 2>&1
    if !errorlevel!==0 set "PYEXE=%%~P"
  )
)
if not defined PYEXE (
  echo [ERROR] Python 3 was not found on this computer.
  echo         Install Python 3.11 or newer from https://www.python.org/downloads/
  echo         and tick "Add Python to PATH" during installation, then run setup.bat again.
  echo.
  pause
  exit /b 1
)
echo Using Python: !PYEXE!
echo.

REM --- 2) Create the virtual environment --------------------------------
if not exist ".venv\Scripts\python.exe" (
  echo Creating an isolated environment in .venv ...
  !PYEXE! -m venv .venv
  if errorlevel 1 (
    echo [ERROR] Could not create the virtual environment.
    pause
    exit /b 1
  )
) else (
  echo Virtual environment already exists - reusing it.
)

set "VENV_PY=.venv\Scripts\python.exe"

REM --- 3) Install dependencies ------------------------------------------
echo.
echo Installing dependencies (this may take a minute the first time)...
"%VENV_PY%" -m pip install --upgrade pip >nul
"%VENV_PY%" -m pip install -r backend\requirements.txt
if errorlevel 1 (
  echo [ERROR] Installing dependencies failed. Please read the messages above.
  pause
  exit /b 1
)

REM --- 4) Create .env and seed the database -----------------------------
echo.
"%VENV_PY%" backend\manage.py setup
if errorlevel 1 (
  echo [ERROR] Setup step failed. Please read the messages above.
  pause
  exit /b 1
)

echo.
echo ============================================================
echo    All done!  Double-click  dev.bat  to start the website.
echo ============================================================
echo.
pause
