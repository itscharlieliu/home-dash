#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PID_FILE="$SCRIPT_DIR/.uvicorn.pid"

if [ ! -f "$PID_FILE" ]; then
  echo "No PID file found at $PID_FILE. Is Home Dash running?"
  exit 1
fi

PID="$(cat "$PID_FILE")"

if ! kill -0 "$PID" >/dev/null 2>&1; then
  echo "Process $PID not running. Removing stale PID file."
  rm -f "$PID_FILE"
  exit 0
fi

echo "Stopping Home Dash (PID $PID)..."
kill "$PID"

for _ in {1..10}; do
  if ! kill -0 "$PID" >/dev/null 2>&1; then
    rm -f "$PID_FILE"
    echo "Home Dash stopped."
    exit 0
  fi
  sleep 0.5
done

echo "Process $PID did not terminate gracefully. Sending SIGKILL."
kill -9 "$PID" || true
rm -f "$PID_FILE"
echo "Home Dash stopped forcefully."

