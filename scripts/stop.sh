#!/bin/bash
set -euo pipefail
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_DIR"

echo "=== 停 xiaozhi-server ==="
XZ_PIDS=$(lsof -ti:8000 -ti:8003 -sTCP:LISTEN 2>/dev/null | sort -u)
if [ -n "$XZ_PIDS" ]; then
  echo "$XZ_PIDS" | xargs kill 2>/dev/null && echo "xiaozhi-server stopped"
else
  echo "no xiaozhi-server running"
fi

echo "=== 停 dispatcher ==="
pkill -f "xiaozhi-hackathon/dispatcher/server.py" && echo "dispatcher stopped" || echo "no dispatcher running"
