@echo off
chcp 65001 >nul
cd /d "%~dp0"
python tower.py init
start "" http://localhost:8765
python tower.py serve
pause
