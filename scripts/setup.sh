#!/bin/bash
# 一键安装:克隆 xiaozhi-server + 装两个 venv + 拷贝配置模板
# 用法: ./scripts/setup.sh
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
XZ_DIR="$PROJECT_DIR/repo/main/xiaozhi-server"
cd "$PROJECT_DIR"

# ── 前置检查 ───────────────────────────────────────────
command -v uv   >/dev/null || { echo "❌ 需要 uv: curl -LsSf https://astral.sh/uv/install.sh | sh"; exit 1; }
command -v git  >/dev/null || { echo "❌ 需要 git"; exit 1; }

echo "=== 1. 克隆 xiaozhi-esp32-server 源码 ==="
if [ -d "$XZ_DIR" ]; then
  echo "xiaozhi-server 已存在,跳过克隆"
elif [ ! -d "repo/.git" ]; then
  git clone --depth=1 https://github.com/xinnan-tech/xiaozhi-esp32-server.git repo
else
  echo "repo/ 已存在,跳过克隆"
fi
if [ ! -d "$XZ_DIR" ]; then
  echo "❌ 未找到 xiaozhi-server 目录: $XZ_DIR"
  echo "   请确认 repo/ 是 xinnan-tech/xiaozhi-esp32-server 源码，或先清理错误的 repo/ 目录。"
  exit 1
fi

echo ""
echo "=== 2. 初始化 xiaozhi-server venv (Python 3.10) ==="
if [ ! -d "$XZ_DIR/.venv" ]; then
  uv python install 3.10 >/dev/null 2>&1 || true
  cd "$XZ_DIR"
  uv venv --python 3.10 .venv
  .venv/bin/python -m ensurepip --upgrade
  .venv/bin/python -m pip install -r requirements.txt
  cd "$PROJECT_DIR"
else
  if "$XZ_DIR/.venv/bin/python" -c "import funasr, mcp, torch, websocket" >/dev/null 2>&1; then
    echo "xiaozhi venv 已存在,跳过"
  else
    echo "xiaozhi venv 不完整,补装依赖"
    cd "$XZ_DIR"
    .venv/bin/python -m ensurepip --upgrade
    .venv/bin/python -m pip install -r requirements.txt
    cd "$PROJECT_DIR"
  fi
fi

echo ""
echo "=== 3. 初始化 dispatcher venv ==="
if [ ! -d "$PROJECT_DIR/dispatcher/.venv" ]; then
  cd "$PROJECT_DIR/dispatcher"
  uv venv .venv
  .venv/bin/python -m ensurepip --upgrade
  .venv/bin/python -m pip install -r requirements.txt
  cd "$PROJECT_DIR"
else
  echo "dispatcher venv 已存在,跳过"
fi

echo ""
echo "=== 4. 建软链:让 xiaozhi-server/data 指向本目录的 data/ ==="
mkdir -p "$XZ_DIR/data"
ln -sfn "$PROJECT_DIR/data/.config.yaml"              "$XZ_DIR/data/.config.yaml"
ln -sfn "$PROJECT_DIR/data/.mcp_server_settings.json" "$XZ_DIR/data/.mcp_server_settings.json"

echo ""
echo "=== 5. 拷贝配置模板(如果还没有) ==="
if [ ! -f "data/.config.yaml" ]; then
  cp data/.config.yaml.example data/.config.yaml
  echo ""
  echo "⚠️  请编辑 data/.config.yaml,把 YOUR_OPENAI_COMPATIBLE_API_KEY 换成你的 key"
  echo "    常见选择:86gamestore / openrouter / 自建中转,必须 OpenAI 兼容 + 支持 function_call"
else
  echo "data/.config.yaml 已存在,未覆盖"
fi

echo ""
echo "=== 6. ASR 模型(SenseVoiceSmall, 首次约 900MB) ==="
MODEL_PT="$PROJECT_DIR/models/SenseVoiceSmall/model.pt"
if [ ! -f "$MODEL_PT" ]; then
  mkdir -p "$PROJECT_DIR/models/SenseVoiceSmall"
  echo "模型会在 xiaozhi-server 首次启动时自动下载到:"
  echo "  $XZ_DIR/models/SenseVoiceSmall/"
  echo "首次启动约 5 分钟,之后本地缓存。"
else
  echo "model.pt 已存在:$MODEL_PT"
fi
# 确保软链到 repo 内部
mkdir -p "$XZ_DIR/models/SenseVoiceSmall"
if [ -f "$MODEL_PT" ] && [ ! -e "$XZ_DIR/models/SenseVoiceSmall/model.pt" ]; then
  ln -sfn "$MODEL_PT" "$XZ_DIR/models/SenseVoiceSmall/model.pt"
fi

echo ""
echo "=== 7. 改小智 core/connection.py(修首轮 MCP 竞态) ==="
CONN="$XZ_DIR/core/connection.py"
if [ -f "$CONN" ] && ! grep -q "_init_wait = 0" "$CONN"; then
  echo "⚠️  你需要手动改 $CONN,参见 README「小智源码改动」章节"
fi

echo ""
echo "✅ 安装完成。下一步:"
echo "   1. 编辑 data/.config.yaml 填 api_key"
echo "   2. 装 OpenClaw Lite 和 Hermes(见 README)"
echo "   3. ./scripts/start.sh"
