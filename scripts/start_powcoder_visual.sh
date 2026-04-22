#!/bin/bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PORT="${POWCODER_VISUAL_PORT:-9200}"

cd "$PROJECT_DIR"
unset http_proxy https_proxy all_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY
export NO_PROXY=127.0.0.1,localhost
export PORT="$PORT"

echo "PowCoder visual dashboard: http://127.0.0.1:${PORT}/"
exec dispatcher/.venv/bin/python powcoder_visual_service/server.py
