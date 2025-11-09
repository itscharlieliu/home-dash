#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

VENV_PATH="$SCRIPT_DIR/.venv"
PID_FILE="$SCRIPT_DIR/.uvicorn.pid"
LOG_DIR="$SCRIPT_DIR/logs"
LOG_FILE="$LOG_DIR/uvicorn.log"

if [ ! -d "$VENV_PATH" ]; then
  python3 -m venv "$VENV_PATH"
fi

# shellcheck disable=SC1090
source "$VENV_PATH/bin/activate"

python -m pip install --upgrade pip
python -m pip install -r requirements.txt

HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

mkdir -p "$LOG_DIR"

if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" >/dev/null 2>&1; then
  echo "Uvicorn appears to be already running (PID $(cat "$PID_FILE"))."
  echo "Stop it first using ./stop.sh or remove $PID_FILE if stale."
  exit 1
fi

echo "Starting Home Dash on $HOST:$PORT..."
nohup uvicorn app.main:app --reload --host "$HOST" --port "$PORT" \
  >>"$LOG_FILE" 2>&1 &
UVICORN_PID=$!
echo "$UVICORN_PID" > "$PID_FILE"
disown "$UVICORN_PID"

echo "Home Dash started in background (PID $UVICORN_PID). Logs: $LOG_FILE"

