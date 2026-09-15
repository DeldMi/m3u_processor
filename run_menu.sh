#!/usr/bin/env bash
set -e
cd "$(dirname "$(readlink -f "$0")")"
if [[ ! -x .venv/bin/python || ! -f frontend/react/dist/index.html ]]; then
	./setup_env.sh
fi
source .venv/bin/activate
echo "[*] Servidor ativo em http://127.0.0.1:5000"
python3 -m src.app