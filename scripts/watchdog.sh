#!/bin/bash

cd "$(dirname "$0")/.." || exit 1
mkdir -p logs
source .venv/bin/activate

while true; do
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] starting uvicorn" >> logs/watchdog.log
  uvicorn app.main:app --host 0.0.0.0 --port 8020 >> logs/chat-api.out.log 2>> logs/chat-api.err.log
  echo "[$(date '+%Y-%m-%d %H:%M:%S')] uvicorn exited (code $?) — restarting in 2s" >> logs/watchdog.log
  sleep 2
done
