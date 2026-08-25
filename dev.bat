@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] The app is not set up yet.
  echo         Please double-click  setup.bat  first.
  echo.
  pause
  exit /b 1
)

echo Starting the website...
echo   Public site:  http://localhost:8000/
echo   Admin panel:  http://localhost:8000/admin
echo.
echo Leave this window open while you use the site. Press CTRL+C to stop.
echo.

".venv\Scripts\python.exe" backend\manage.py dev

pause
