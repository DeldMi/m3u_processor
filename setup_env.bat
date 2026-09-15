@echo off
setlocal
cd /d "%~dp0"
title Setup do Ambiente M3U Architect

where python >nul 2>&1 || (echo [ERRO] Python nao encontrado no PATH.& exit /b 1)
where npm >nul 2>&1 || (echo [ERRO] Node.js/npm nao encontrado no PATH.& echo Instale Node.js LTS e execute este script novamente.& exit /b 1)

if not exist ".venv\Scripts\python.exe" python -m venv .venv || exit /b 1
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip || exit /b 1
python -m pip install -r requirements.txt || exit /b 1

cd frontend\react
if exist package-lock.json (npm ci) else (npm install)
if errorlevel 1 exit /b 1
npm run build
if errorlevel 1 exit /b 1

cd /d "%~dp0"
if not exist ".env" copy /y "exeplo.env" ".env" >nul
echo [OK] Ambiente Python e frontend React configurados.
endlocal