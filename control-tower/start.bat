@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo Python is not installed. Install Python 3 from python.org and check "Add Python to PATH".
  pause
  exit /b 1
)
python tower.py init
start "" http://localhost:8765
python tower.py serve
pause
