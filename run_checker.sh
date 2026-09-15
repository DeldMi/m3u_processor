#!/usr/bin/env bash
source .venv/bin/activate
python3 -c "from src.app import execute_pipeline; execute_pipeline()"