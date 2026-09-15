@echo off
setlocal
cd /d "%~dp0"
title Painel IPTV e Auditoria M3U
if not exist ".venv\Scripts\python.exe" call setup_env.bat || exit /b 1
if not exist "frontend\react\dist\index.html" call setup_env.bat || exit /b 1
call .venv\Scripts\activate.bat
start "" http://127.0.0.1:5000
python -m src.app
endlocal