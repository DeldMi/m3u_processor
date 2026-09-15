@echo off
title Processador M3U - Modo Terminal
call .venv\Scripts\activate.bat
python -c "from src.app import execute_pipeline; execute_pipeline()"
pause