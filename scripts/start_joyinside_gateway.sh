#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${JOYINSIDE_GATEWAY_PORT:-9100}"

if [ -f "$PROJECT_DIR/.env" ]; then
  set -a
  # shellcheck disable=SC1091
  source "$PROJECT_DIR/.env"
  set +a
fi

if [ -z "${JOYINSIDE_SERVICE_TOKEN:-}" ]; then
  echo "❌ 请先设置 JOYINSIDE_SERVICE_TOKEN"
  echo "   示例: JOYINSIDE_SERVICE_TOKEN=dev-token ./scripts/start_joyinside_gateway.sh"
  exit 1
fi

if nc -z 127.0.0.1 "$PORT" 2>/dev/null; then
  echo "❌ 端口 ${PORT} 已被占用"
  exit 1
fi

cd "$PROJECT_DIR"
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export NO_PROXY=127.0.0.1,localhost
export PORT="$PORT"

echo "JoyInside gateway: http://127.0.0.1:${PORT}/joyinside/skill"
exec dispatcher/.venv/bin/python joyinside_gateway/server.py
