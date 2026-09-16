#!/usr/bin/env bash
set -e
set -u
cd "$(dirname "$(readlink -f "$0")")"

command -v python3 >/dev/null || { echo "[ERRO] Python 3 nao encontrado no PATH."; exit 1; }
command -v npm >/dev/null || { echo "[ERRO] Node.js/npm nao encontrado no PATH."; exit 1; }

echo "[*] Alocando ambiente virtual Linux (.venv)..."
[[ -x .venv/bin/python ]] || python3 -m venv .venv
source .venv/bin/activate
echo "[*] Instalando dependencias Python..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo "[*] Instalando e compilando frontend React..."
cd frontend/react
if [[ -f package-lock.json ]]; then npm ci; else npm install; fi
npm run build
cd ../..
if [[ ! -f .env ]]; then
    if [[ -f .env.example ]]; then
        cp .env.example .env
    elif [[ -f exeplo.env ]]; then
        cp exeplo.env .env
    fi
fi
echo "[OK] Ambiente Python e frontend React configurados."