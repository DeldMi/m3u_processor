@echo off
title Servidor e Agendador de Listas M3U
call .venv\Scripts\activate.bat
start "" http://127.0.0.1:5000
python -m src.app
pause