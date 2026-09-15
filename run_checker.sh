#!/usr/bin/env bash
set -e
cd "$(dirname "$(readlink -f "$0")")"
if [[ ! -x .venv/bin/python || ! -f frontend/react/dist/index.html ]]; then
	./setup_env.sh
fi
source .venv/bin/activate
python3 -c "from src.app import execute_pipeline; execute_pipeline()"