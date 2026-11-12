@echo off
cd /d "%~dp0.."
if not exist ".venv\Scripts\python.exe" (
  echo Set up the project environment first. See README.md.
  pause
  exit /b 1
)
set MPLBACKEND=Agg
set PYTHONUTF8=1
".venv\Scripts\python.exe" app\server.py --open
if errorlevel 1 pause
