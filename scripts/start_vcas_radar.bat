@echo off
setlocal

cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo Missing .venv\Scripts\python.exe. Run:
  echo   uv sync
  echo in the repository root first.
  exit /b 1
)

echo Starting vCAS API on http://localhost:8000
set PYTHONPATH=%CD%
".venv\Scripts\python.exe" -m uvicorn vcas.api.main:app --app-dir src --host 0.0.0.0 --port 8000
