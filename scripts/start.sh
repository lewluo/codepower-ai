#!/bin/bash
# 一键启动 xiaozhi-server(源码) + dispatcher
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XZ_DIR="$PROJECT_DIR/repo/main/xiaozhi-server"
DISPATCHER_PORT="${DISPATCHER_PORT:-9001}"
cd "$PROJECT_DIR"

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.env"
  set +a
fi

echo "=== 1. 启动 MCP dispatcher (host:${DISPATCHER_PORT}) ==="
if nc -z 127.0.0.1 "$DISPATCHER_PORT" 2>/dev/null; then
  echo "❌ 端口 ${DISPATCHER_PORT} 已被占用。请先停止占用进程,或用 DISPATCHER_PORT=xxxx 指定新端口。"
  exit 1
fi
sleep 1

cd "$PROJECT_DIR/dispatcher"
source .venv/bin/activate
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export NO_PROXY=127.0.0.1,localhost

PORT="$DISPATCHER_PORT" nohup python3 server.py > "$PROJECT_DIR/dispatcher.log" 2>&1 < /dev/null &
DISPATCHER_PID=$!
echo "$DISPATCHER_PID" > "$PROJECT_DIR/dispatcher.pid"
echo "dispatcher PID=$DISPATCHER_PID -> $PROJECT_DIR/dispatcher.log"
sleep 2

if ! curl -sf -o /dev/null -w "%{http_code}" \
     -X POST -H "Content-Type: application/json" \
     -H "Accept: application/json, text/event-stream" \
     -d '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","capabilities":{},"clientInfo":{"name":"start-sh","version":"1.0"}}}' \
     "http://127.0.0.1:${DISPATCHER_PORT}/mcp" | grep -q 200; then
  echo "❌ dispatcher 未起来,看 dispatcher.log"
  exit 1
fi
echo "✅ dispatcher 已就绪"
deactivate
echo ""

echo "=== 2. 启动 xiaozhi-server (Python 源码, ARM64 原生) ==="
if nc -z 127.0.0.1 8000 2>/dev/null || nc -z 127.0.0.1 8003 2>/dev/null; then
  echo "❌ 端口 8000 或 8003 已被占用。请先运行 ./scripts/stop.sh 或手动停止占用进程。"
  exit 1
fi
sleep 1

cd "$XZ_DIR"
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export NO_PROXY=127.0.0.1,localhost
nohup ./.venv/bin/python app.py > "$PROJECT_DIR/xiaozhi-server.log" 2>&1 < /dev/null &
XZ_PID=$!
echo "$XZ_PID" > "$PROJECT_DIR/xiaozhi-server.pid"
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
LAN_IP="${LAN_IP:-$(ipconfig getifaddr en0 2>/dev/null || true)}"
LAN_IP="${LAN_IP:-127.0.0.1}"
echo "WebSocket: ws://127.0.0.1:8000/xiaozhi/v1/"
echo "LAN WebSocket: ws://${LAN_IP}:8000/xiaozhi/v1/"
echo "HTTP:      http://127.0.0.1:8003/"
echo "OTA:       http://${LAN_IP}:8003/xiaozhi/ota/"
echo "测试网页:  open $XZ_DIR/test/test_page.html"
echo ""
echo "=== 4. 日志 ==="
echo "tail -f $PROJECT_DIR/xiaozhi-server.log"
echo "tail -f $PROJECT_DIR/dispatcher.log"
