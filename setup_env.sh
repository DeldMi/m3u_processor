#!/usr/bin/env bash
set -e
echo "[*] Criando ambiente virtual Linux (.venv)..."
python3 -m venv .venv
source .venv/bin/activate
echo "[*] Instalando dependencias..."
pip install --upgrade pip
pip install -r requirements.txt
echo "[OK] Ambiente Linux configurado."