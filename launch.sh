#!/usr/bin/env bash
set -euo pipefail

APP_DIR="/home/romeruu/png2vlsi_pixel"
PYTHON_BIN="$APP_DIR/.venv/bin/python"

if [[ ! -x "$PYTHON_BIN" ]]; then
  PYTHON_BIN="python3"
fi

cd "$APP_DIR"
exec "$PYTHON_BIN" "$APP_DIR/run_app.py"
