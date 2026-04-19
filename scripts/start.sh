#!/bin/bash
# 一键启动 xiaozhi-server(源码) + dispatcher
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XZ_DIR="$PROJECT_DIR/repo/main/xiaozhi-server"
cd "$PROJECT_DIR"

echo "=== 1. 启动 MCP dispatcher (host:9000) ==="
pkill -f "xiaozhi-hackathon/dispatcher/server.py" 2>/dev/null || true
sleep 1

cd "$PROJECT_DIR/dispatcher"
source .venv/bin/activate
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export NO_PROXY=127.0.0.1,localhost

nohup python3 server.py > "$PROJECT_DIR/dispatcher.log" 2>&1 &
DISPATCHER_PID=$!
echo "dispatcher PID=$DISPATCHER_PID -> $PROJECT_DIR/dispatcher.log"
sleep 2

if ! curl -sf -o /dev/null -w "%{http_code}" \
     -X POST -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"start-sh","version":"1.0"}}}' \
     http://127.0.0.1:9000/mcp | grep -q 200; then
  echo "❌ dispatcher 未起来,看 dispatcher.log"
  exit 1
fi
echo "✅ dispatcher 已就绪"
deactivate
echo ""

echo "=== 2. 启动 xiaozhi-server (Python 源码, ARM64 原生) ==="
lsof -ti:8000 -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null || true
lsof -ti:8003 -sTCP:LISTEN 2>/dev/null | xargs -r kill 2>/dev/null || true
sleep 1

cd "$XZ_DIR"
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export NO_PROXY=127.0.0.1,localhost
nohup ./.venv/bin/python app.py > "$PROJECT_DIR/xiaozhi-server.log" 2>&1 &
XZ_PID=$!
echo "xiaozhi-server PID=$XZ_PID -> $PROJECT_DIR/xiaozhi-server.log"

# 等 WebSocket 端口就绪(最多 60s — ASR 模型加载慢)
for i in $(seq 1 60); do
  if nc -z 127.0.0.1 8000 2>/dev/null; then
    echo "✅ xiaozhi-server 已就绪 (用时 ${i}s)"
    break
  fi
  sleep 1
done
if ! nc -z 127.0.0.1 8000 2>/dev/null; then
  echo "❌ xiaozhi-server 60s 内未起来,看 xiaozhi-server.log"
  tail -30 "$PROJECT_DIR/xiaozhi-server.log"
  exit 1
fi

echo ""
echo "=== 3. 访问方式 ==="
echo "WebSocket: ws://127.0.0.1:8000/xiaozhi/v1/"
echo "HTTP:      http://127.0.0.1:8003/"
echo "测试网页:  open $XZ_DIR/test/test_page.html"
echo ""
echo "=== 4. 日志 ==="
echo "tail -f $PROJECT_DIR/xiaozhi-server.log"
echo "tail -f $PROJECT_DIR/dispatcher.log"
