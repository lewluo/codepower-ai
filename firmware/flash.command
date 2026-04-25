#!/bin/zsh

set -u
setopt null_glob

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IDF_PATH="/Users/jaydenworkplace/esp/esp-idf"
IDF_PYTHON="/Users/jaydenworkplace/.espressif/python_env/idf5.4_py3.14_env/bin/python"
IDF_TOOLS_PATH="/Users/jaydenworkplace/.espressif"

pause_and_exit() {
  local code="${1:-0}"
  echo
  read "?按回车退出..."
  exit "$code"
}

choose_port() {
  local -a ports
  ports=(/dev/cu.usbmodem* /dev/cu.usbserial*)

  if (( ${#ports[@]} == 0 )); then
    echo "未找到可用串口。" >&2
    return 1
  fi

  if (( ${#ports[@]} == 1 )); then
    echo "${ports[1]}"
    return 0
  fi

  echo "检测到多个串口：" >&2
  local i=1
  for port in "${ports[@]}"; do
    echo "  [$i] $port" >&2
    ((i++))
  done

  echo >&2
  read "?请输入串口编号(输入 1、2 这种序号): " index
  if [[ -z "${index:-}" || ! "$index" =~ '^[0-9]+$' || "$index" -lt 1 || "$index" -gt ${#ports[@]} ]]; then
    echo "串口编号无效。" >&2
    return 1
  fi

  echo "${ports[$index]}"
}

echo "项目目录: $SCRIPT_DIR"
echo "加载 ESP-IDF 环境..."

if [[ ! -f "$IDF_PATH/export.sh" ]]; then
  echo "未找到 ESP-IDF: $IDF_PATH"
  pause_and_exit 1
fi

if [[ ! -x "$IDF_PYTHON" ]]; then
  echo "未找到 ESP-IDF Python: $IDF_PYTHON"
  pause_and_exit 1
fi

cd "$SCRIPT_DIR" || pause_and_exit 1

export IDF_TOOLS_PATH
export IDF_PYTHON_ENV_PATH="$(dirname "$(dirname "$IDF_PYTHON")")"
source "$IDF_PATH/export.sh" || pause_and_exit 1

PORT="$(choose_port)" || pause_and_exit 1

echo
echo "使用串口: $PORT"
echo "开始烧录..."
echo

"$IDF_PYTHON" "$IDF_PATH/tools/idf.py" -p "$PORT" flash
STATUS=$?

echo
if [[ $STATUS -eq 0 ]]; then
  echo "烧录完成。"
else
  echo "烧录失败，退出码: $STATUS"
fi

pause_and_exit "$STATUS"
