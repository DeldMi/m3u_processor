@echo off
setlocal
cd /d "%~dp0"
title Processador M3U - Modo Terminal
if not exist ".venv\Scripts\python.exe" call setup_env.bat || exit /b 1
call .venv\Scripts\activate.bat
python -c "from src.app import execute_pipeline; execute_pipeline()"
endlocal