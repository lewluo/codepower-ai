#!/bin/bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== 停 xiaozhi-server ==="
if [ -f "$PROJECT_DIR/xiaozhi-server.pid" ]; then
  XZ_PID=$(cat "$PROJECT_DIR/xiaozhi-server.pid")
  if ps -p "$XZ_PID" >/dev/null 2>&1; then
    kill "$XZ_PID" 2>/dev/null && echo "xiaozhi-server stopped"
  else
    echo "xiaozhi-server pid 不存在"
  fi
  rm -f "$PROJECT_DIR/xiaozhi-server.pid"
else
  echo "no xiaozhi-server running"
fi

echo "=== 停 dispatcher ==="
if [ -f "$PROJECT_DIR/dispatcher.pid" ]; then
  DISPATCHER_PID=$(cat "$PROJECT_DIR/dispatcher.pid")
  if ps -p "$DISPATCHER_PID" >/dev/null 2>&1; then
    kill "$DISPATCHER_PID" 2>/dev/null && echo "dispatcher stopped"
  else
    echo "dispatcher pid 不存在"
  fi
  rm -f "$PROJECT_DIR/dispatcher.pid"
else
  echo "no dispatcher running"
fi
