@echo off
title Instalacao de Ambiente Virtual
echo [*] Criando ambiente virtual Python (.venv)...
python -m venv .venv
if %ERRORLEVEL% neq 0 (
    echo [ERRO] Falha ao invocar python. Verifique se o interpretador esta no PATH.
    pause
    exit /b 1
)
call .venv\Scripts\activate.bat
echo [*] Instalando bibliotecas requeridas...
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Ambiente isolado configurado com sucesso.
pause