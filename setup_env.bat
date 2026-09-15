@echo off
title Setup do Ambiente Virtual
python -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
pip install -r requirements.txt
echo [OK] Ambiente configurado.
pause