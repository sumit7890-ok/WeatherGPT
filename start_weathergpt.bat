@echo off
title WeatherGPT - MoES/IMD Intelligent Meteorological Server
echo ========================================================
echo   Starting WeatherGPT FastAPI Server on Port 8000
echo   Access UI at: http://localhost:8000
echo ========================================================

cd /d "%~dp0"

if exist ".venv\Scripts\python.exe" (
    set PYTHON_EXE=.venv\Scripts\python.exe
) else (
    set PYTHON_EXE=python
)

start http://localhost:8000
%PYTHON_EXE% -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000

pause
