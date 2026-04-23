"""
CodePower Dispatcher — 小智语音的后端工具服务
架构: 小智(Docker) → streamable-http MCP → 本服务(host:9000) → 可配置任务后端 / Codex / Claude Code

工具:
  list_agents()                    - 列出可用 agent
  list_agent_backends()            - 列出可用任务后端
  dispatch_agent(agent_id, task)   - 按配置派发任务
  openclaw_agent_task(...)         - 可选: 调完整 OpenClaw Gateway agent
  query_agent_status()             - 查询最近一次派发状态
  read_daily_report(date='today')  - 读 OpenClaw 日报
  hermes_repo_task(task)           - 可选: 调 Hermes 在专用工作目录执行仓库任务
  run_codex(task, ...)             - 调本机 Codex CLI
  run_claude_code(task, ...)       - 调本机 Claude Code CLI
"""
from __future__ import annotations

import asyncio
import binascii
import hashlib
import hmac
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
import websocket
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

try:
    from powcoder_visual import state as visual_state
except Exception:
    visual_state = None

# 加载上级目录的 .env（所有 os.environ.get 之前）
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

HOME = Path.home()
AGENTS_JSON = HOME / ".openclaw/lite/agents.json"
DISPATCH_SH = HOME / ".openclaw/lite/bin/dispatch.sh"
DAILY_LOG_DIR = HOME / ".openclaw/workspace/logs/daily"
HERMES = HOME / ".local/bin/hermes"
OPENCLAW_BIN_RAW = os.environ.get("CODEPOWER_OPENCLAW_BIN", "openclaw")
OPENCLAW = (
    str(Path(OPENCLAW_BIN_RAW).expanduser())
    if "/" in OPENCLAW_BIN_RAW
    else shutil.which(OPENCLAW_BIN_RAW)
)
CODEX = shutil.which("codex")
CLAUDE = shutil.which("claude")
WORKSPACE_DIR = Path(
    os.environ.get(
        "CODEPOWER_HERMES_WORKSPACE",
        str(HOME / "Desktop/work_space/hemers_work_dir"),
    )
).expanduser()

STATE_FILE = Path("/tmp/xiaozhi-dispatcher-state.json")
RUNS_DIR = Path("/tmp/xiaozhi-dispatcher-runs")
RUNS_DIR.mkdir(exist_ok=True)

HERMES_TIMEOUT_SEC = 600         # 10 分钟
HERMES_REPO_TIMEOUT_SEC = 600
OPENCLAW_AGENT_TIMEOUT_SEC = int(os.environ.get("CODEPOWER_OPENCLAW_AGENT_TIMEOUT_SEC", "600"))
OPENCLAW_AGENT_LIST_TIMEOUT_SEC = int(os.environ.get("CODEPOWER_OPENCLAW_AGENT_LIST_TIMEOUT_SEC", "8"))
OPENCLAW_DEFAULT_AGENT_ID = os.environ.get("CODEPOWER_OPENCLAW_DEFAULT_AGENT") or "planner"
AGENT_DEFAULT_ID = os.environ.get("CODEPOWER_DEFAULT_AGENT") or "planner"
AGENT_REGISTRY_CONFIG = os.environ.get("CODEPOWER_AGENT_REGISTRY", "")
OPENCLAW_THINKING = os.environ.get("CODEPOWER_OPENCLAW_THINKING", "")
OPENCLAW_GATEWAY_URL = os.environ.get("CODEPOWER_OPENCLAW_GATEWAY_URL", "ws://127.0.0.1:18789")
OPENCLAW_LITE_TIMEOUT_SEC = int(os.environ.get("CODEPOWER_OPENCLAW_LITE_TIMEOUT_SEC", "300"))
AGENT_BACKEND = os.environ.get("CODEPOWER_AGENT_BACKEND") or "hermes"
AGENT_BACKENDS = tuple(
    item.strip().lower()
    for item in (os.environ.get("CODEPOWER_AGENT_BACKENDS") or "hermes,openclaw").split(",")
    if item.strip()
)
AGENT_FALLBACK_BACKENDS = tuple(
    item.strip().lower()
    for item in os.environ.get("CODEPOWER_AGENT_FALLBACK_BACKENDS", "").split(",")
    if item.strip()
)
CODEX_TIMEOUT_SEC = 600
CLAUDE_CODE_TIMEOUT_SEC = 600
JOYINSIDE_TIMEOUT_SEC = 20
JOYINSIDE_MAX_WAIT_SEC = 60

# Resend Email
RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
RESEND_FROM_NAME = os.environ.get("RESEND_FROM_NAME", "PowCoder")
RESEND_FROM_EMAIL = os.environ.get("RESEND_FROM_EMAIL", "hello@notify.powcoder.space")
RESEND_CONTACTS_RAW = os.environ.get("RESEND_CONTACTS", "")
RESEND_CONTACTS = {}
for pair in RESEND_CONTACTS_RAW.split(","):
    pair = pair.strip()
    if ":" in pair:
        name, email = pair.split(":", 1)
        RESEND_CONTACTS[name.strip()] = email.strip()

JOYINSIDE_AUTH_URL = os.environ.get(
    "JOYINSIDE_AUTH_URL", "https://api.joyinside.com/auth/getToken"
)
JOYINSIDE_REGISTER_URL = os.environ.get(
    "JOYINSIDE_REGISTER_URL", "https://api.joyinside.com/device/register"
)
JOYINSIDE_WS_URL = os.environ.get(
    "JOYINSIDE_WS_URL", "wss://ws.joyinside.com/soulmate/voiceChat/v1"
)
JOYINSIDE_ACCESS_KEY = os.environ.get("JOYINSIDE_ACCESS_KEY", "")
JOYINSIDE_SECRET_KEY = os.environ.get("JOYINSIDE_SECRET_KEY", "")
JOYINSIDE_VENDOR_ID = os.environ.get("JOYINSIDE_VENDOR_ID", "")
JOYINSIDE_APP_ID = os.environ.get("JOYINSIDE_APP_ID", "")
JOYINSIDE_BOT_ID = os.environ.get("JOYINSIDE_BOT_ID", "")
JOYINSIDE_DEVICE_ID = os.environ.get("JOYINSIDE_DEVICE_ID", "codepower-local-xiaozhi")
JOYINSIDE_DEVICE_NAME = os.environ.get("JOYINSIDE_DEVICE_NAME", "CodePower-Local-Xiaozhi")
JOYINSIDE_UID = os.environ.get("JOYINSIDE_UID", "codepower-local-user")
_JOYINSIDE_TOKEN_CACHE: dict[str, tuple[str, float]] = {}

mcp = FastMCP("codepower-dispatcher")
_OPENCLAW_AGENTS_CACHE: tuple[float, dict] = (0.0, {})
_BACKGROUND_TASKS: set[asyncio.Task] = set()
_BUILTIN_AGENT_ROLES = {
    "planner": "任务规划、分派与协调",
    "executor": "通用任务执行与结果整理",
}


def _parse_first_json_value(text: str):
    decoder = json.JSONDecoder()
    for index, char in enumerate(text):
        if char not in "[{":
            continue
        try:
            value, _ = decoder.raw_decode(text[index:])
            return value
        except json.JSONDecodeError:
            continue
    return None


def _load_lite_agents() -> dict:
    if not AGENTS_JSON.exists():
        return {}
    with AGENTS_JSON.open() as f:
        return json.load(f).get("agents", {})


def _enabled_backend_names() -> set[str]:
    names = {_normalize_backend(item) for item in AGENT_BACKENDS}
    if AGENT_BACKEND:
        names.add(_normalize_backend(AGENT_BACKEND))
    return {item for item in names if item}


def _load_configured_agents() -> dict:
    agents: dict[str, dict] = {}
    for item in AGENT_REGISTRY_CONFIG.split(","):
        raw = item.strip()
        if not raw:
            continue
        if ":" in raw:
            agent_id, role = raw.split(":", 1)
        elif "=" in raw:
            agent_id, role = raw.split("=", 1)
        else:
            agent_id, role = raw, raw
        agent_id = agent_id.strip()
        role = role.strip() or agent_id
        if not agent_id:
            continue
        agents[agent_id] = {
            "role": role,
            "emoji": "",
            "workspace": "",
            "model": "",
            "is_default": agent_id == AGENT_DEFAULT_ID,
            "source": "config",
        }
    return agents


def _load_builtin_agents() -> dict:
    agents: dict[str, dict] = {}
    for agent_id, role in _BUILTIN_AGENT_ROLES.items():
        agents[agent_id] = {
            "role": role,
            "emoji": "",
            "workspace": "",
            "model": "",
            "is_default": agent_id == AGENT_DEFAULT_ID,
            "source": "builtin",
        }
    return agents


def _load_openclaw_agents() -> dict:
    global _OPENCLAW_AGENTS_CACHE
    cached_at, cached = _OPENCLAW_AGENTS_CACHE
    if cached and time.time() - cached_at < 60:
        return cached
    if not OPENCLAW:
        return {}
    try:
        proc = subprocess.run(
            [OPENCLAW, "agents", "list", "--json"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=OPENCLAW_AGENT_LIST_TIMEOUT_SEC,
            check=False,
        )
    except Exception:
        return {}
    if proc.returncode != 0:
        return {}
    data = _parse_first_json_value(proc.stdout or "")
    if not isinstance(data, list):
        return {}
    agents: dict[str, dict] = {}
    for item in data:
        if not isinstance(item, dict):
            continue
        agent_id = str(item.get("id") or "").strip()
        if not agent_id:
            continue
        agents[agent_id] = {
            "role": item.get("identityName") or item.get("name") or agent_id,
            "emoji": item.get("identityEmoji") or "",
            "workspace": item.get("workspace") or "",
            "model": item.get("model") or "",
            "is_default": bool(item.get("isDefault")),
            "source": "openclaw",
        }
    if agents:
        _OPENCLAW_AGENTS_CACHE = (time.time(), agents)
    return agents


def _load_agent_registry() -> tuple[dict, str]:
    agents = _load_configured_agents()
    if agents:
        return agents, "config"
    return _load_builtin_agents(), "builtin"


def _load_agents() -> dict:
    return _load_agent_registry()[0]


def _agent_role_prompt(agent_id: str) -> str:
    agents = _load_agents()
    a = agents.get(agent_id)
    if not a:
        return f"你是一个 {agent_id} agent,请完成以下任务。"
    role = a.get("role", agent_id)
    emoji = a.get("emoji", "")
    return f"你的角色: {emoji} {role}\n请基于你的角色完成任务。"


def _save_state(data: dict) -> None:
    STATE_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text())
    except Exception:
        return {}


def _visual_start_worker(**kwargs) -> None:
    if visual_state is None:
        return
    try:
        visual_state.start_worker(**kwargs)
    except Exception as e:
        print(f"[visual_state] start_worker failed: {type(e).__name__}: {e}")


def _visual_finish_worker(**kwargs) -> None:
    if visual_state is None:
        return
    try:
        visual_state.finish_worker(**kwargs)
    except Exception as e:
        print(f"[visual_state] finish_worker failed: {type(e).__name__}: {e}")


def _persist_run_state(state: dict) -> None:
    _save_state(state)
    run_id = state.get("run_id")
    if run_id:
        (RUNS_DIR / f"{run_id}.json").write_text(
            json.dumps(state, ensure_ascii=False, indent=2)
        )


def _track_background_task(task: asyncio.Task) -> None:
    _BACKGROUND_TASKS.add(task)
    task.add_done_callback(_BACKGROUND_TASKS.discard)


async def _run_hermes(
    task_prompt: str, timeout: int, cwd: Optional[Path] = None
) -> tuple[bool, str]:
    """调 Hermes 非交互模式,返回 (成功, 结果文本)"""
    if not HERMES.exists():
        return False, "Hermes 未安装"
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            str(HERMES), "chat",
            "-q", task_prompt,
            "-Q",                       # quiet: 只输出最终回复
            "--yolo",                   # 跳过确认
            "--source", "tool",         # 不污染会话列表
            cwd=str(cwd) if cwd else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        text = out.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            err_text = err.decode("utf-8", errors="replace").strip()
            detail = err_text or text or "no stderr/stdout"
            return False, f"Hermes exit={proc.returncode}: {detail[:500]}"
        if not text:
            return False, "Hermes 返回为空"
        # 清理 Hermes 非内容行(session_id、空行等),语音场景不需要
        clean_lines = [l for l in text.splitlines() if l.strip() and not l.startswith("session_id:")]
        return True, "\n".join(clean_lines).strip()
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return False, f"Hermes 超时 ({timeout}s)"
    except asyncio.CancelledError:
        try:
            if proc and proc.returncode is None:
                proc.kill()
        except Exception:
            pass
        raise
    except Exception as e:
        return False, f"Hermes 异常: {type(e).__name__}: {e}"


def _extract_openclaw_text(data: dict) -> str:
    result = data.get("result")
    if isinstance(result, dict):
        payloads = result.get("payloads")
        if isinstance(payloads, list):
            parts = [
                str(item.get("text") or "").strip()
                for item in payloads
                if isinstance(item, dict) and str(item.get("text") or "").strip()
            ]
            if parts:
                return "\n".join(parts)
        for key in ("finalAssistantVisibleText", "finalAssistantRawText", "text"):
            value = result.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
    for key in ("summary", "message", "text"):
        value = data.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


async def _run_openclaw_agent(agent_id: str, task: str, timeout: int) -> tuple[bool, str]:
    """调完整 OpenClaw Gateway agent,返回 (成功, 结果文本)。"""
    if not OPENCLAW:
        return False, "OpenClaw CLI 未安装或不在 PATH 中。"
    cmd = [
        OPENCLAW,
        "agent",
        "--agent",
        agent_id,
        "--message",
        task,
        "--json",
        "--timeout",
        str(timeout),
    ]
    if OPENCLAW_THINKING:
        cmd += ["--thinking", OPENCLAW_THINKING]
    proc = None
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout + 20)
        text = out.decode("utf-8", errors="replace")
        data = _parse_first_json_value(text)
        if not isinstance(data, dict):
            if proc.returncode != 0:
                return False, f"OpenClaw exit={proc.returncode}: {text[:500]}"
            return True, text.strip() or "(无输出)"
        result_text = _extract_openclaw_text(data) or "(无输出)"
        if proc.returncode != 0 or data.get("status") not in (None, "ok", "success"):
            status = data.get("status") or f"exit={proc.returncode}"
            return False, f"OpenClaw {status}: {result_text[:500]}"
        return True, result_text
    except asyncio.CancelledError:
        try:
            if proc and proc.returncode is None:
                proc.kill()
        except Exception:
            pass
        return False, "OpenClaw 调用被上游连接取消"
    except asyncio.TimeoutError:
        try:
            if proc and proc.returncode is None:
                proc.kill()
        except Exception:
            pass
        return False, f"OpenClaw 超时 ({timeout}s)"
    except Exception as e:
        return False, f"OpenClaw 异常: {type(e).__name__}: {e}"


async def _run_claude_dispatch(agent_id: str, task: str, timeout: int) -> tuple[bool, str]:
    """调 OpenClaw Lite dispatch.sh,返回 (成功, 结果文本)。保留为显式 legacy 后端。"""
    if not DISPATCH_SH.exists():
        return False, "dispatch.sh 不存在"
    try:
        proc = await asyncio.create_subprocess_exec(
            str(DISPATCH_SH), agent_id, task, "--sync",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        text = out.decode("utf-8", errors="replace")
        # 截取 DISPATCH_RESULT 块里的 result 字段
        marker = "---DISPATCH_RESULT---"
        if marker in text:
            body = text.split(marker, 1)[1]
            result_idx = body.find("result:")
            if result_idx > 0:
                text = body[result_idx + len("result:"):].strip()
        if proc.returncode != 0:
            return False, f"Claude 派发失败 (exit={proc.returncode}): {text[:500]}"
        return True, text.strip() or "(无输出)"
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return False, f"Claude 派发超时 ({timeout}s)"
    except Exception as e:
        return False, f"Claude 派发异常: {type(e).__name__}: {e}"


async def _run_command(cmd: list[str], timeout: int, cwd: Path) -> tuple[bool, str]:
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        out, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        text = out.decode("utf-8", errors="replace").strip()
        if proc.returncode != 0:
            return False, f"exit={proc.returncode}: {text[:1200]}"
        return True, text or "(无输出)"
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return False, f"超时 ({timeout}s)"
    except Exception as e:
        return False, f"{type(e).__name__}: {e}"


def _resolve_workdir(workdir: Optional[str]) -> Path:
    if not workdir:
        return Path.cwd()
    path = Path(workdir).expanduser()
    if not path.is_absolute():
        path = Path.cwd() / path
    return path.resolve()


def _joyinside_missing_config() -> list[str]:
    required = {
        "JOYINSIDE_ACCESS_KEY": JOYINSIDE_ACCESS_KEY,
        "JOYINSIDE_SECRET_KEY": JOYINSIDE_SECRET_KEY,
        "JOYINSIDE_VENDOR_ID": JOYINSIDE_VENDOR_ID,
        "JOYINSIDE_APP_ID": JOYINSIDE_APP_ID,
    }
    return [name for name, value in required.items() if not value]


def _joyinside_sign(params: dict[str, str]) -> str:
    lower_params = {key.lower(): str(value) for key, value in params.items()}
    joint_params = "&".join(
        f"{key}={value}" for key, value in sorted(lower_params.items())
    )
    digest = hmac.new(
        JOYINSIDE_SECRET_KEY.encode("utf-8"),
        joint_params.encode("utf-8"),
        digestmod=hashlib.md5,
    ).digest()
    return binascii.hexlify(digest).decode("utf-8")


def _joyinside_auth_payload() -> dict[str, str]:
    params = {
        "accessKeyId": JOYINSIDE_ACCESS_KEY,
        "accessTimestamp": str(int(time.time() * 1000)),
        "accessNonce": str(uuid.uuid4()),
        "accessVersion": "V2",
    }
    params["accessSign"] = _joyinside_sign(params)
    return params


def _joyinside_post(url: str, **kwargs) -> requests.Response:
    session = requests.Session()
    session.trust_env = False
    return session.post(url, timeout=JOYINSIDE_TIMEOUT_SEC, **kwargs)


def _joyinside_get_token(*, bot_id: str | None = None) -> str:
    scope = f"bot:{bot_id}" if bot_id else f"vendor:{JOYINSIDE_VENDOR_ID}"
    cached = _JOYINSIDE_TOKEN_CACHE.get(scope)
    now = time.time()
    if cached and now < cached[1] - 60:
        return cached[0]

    payload = _joyinside_auth_payload()
    if bot_id:
        payload["botId"] = bot_id
    else:
        payload["vendorId"] = JOYINSIDE_VENDOR_ID

    response = _joyinside_post(JOYINSIDE_AUTH_URL, json=payload)
    response.raise_for_status()
    data = response.json()
    token = data.get("accessToken")
    if not token:
        raise RuntimeError(
            f"JoyInside 获取 token 失败: code={data.get('code')} msg={data.get('msg')}"
        )
    _JOYINSIDE_TOKEN_CACHE[scope] = (token, now + int(data.get("expireIn", 7200)))
    return token


def _joyinside_register_device() -> str:
    token = _joyinside_get_token()
    payload = {
        "vendorId": JOYINSIDE_VENDOR_ID,
        "appId": JOYINSIDE_APP_ID,
        "type": "APP_ROBOT",
        "name": JOYINSIDE_DEVICE_NAME,
        "deviceId": JOYINSIDE_DEVICE_ID,
        "deviceModel": "codepower-xiaozhi-tool",
        "desc": "CodePower dispatcher to JoyInside tool bridge",
    }
    response = _joyinside_post(
        JOYINSIDE_REGISTER_URL,
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    response.raise_for_status()
    data = response.json()
    bot_id = data.get("data")
    if not bot_id:
        raise RuntimeError(
            f"JoyInside 注册设备失败: state={data.get('state')} code={data.get('code')} result={data.get('result')}"
        )
    return bot_id


def _joyinside_resolve_bot_id() -> str:
    global JOYINSIDE_BOT_ID
    if JOYINSIDE_BOT_ID:
        return JOYINSIDE_BOT_ID
    JOYINSIDE_BOT_ID = _joyinside_register_device()
    return JOYINSIDE_BOT_ID


def _joyinside_chat_sync(input: str, session_id: str = "codepower-tool") -> str:
    missing = _joyinside_missing_config()
    if missing:
        return f"JoyInside 未配置: {', '.join(missing)}"
    if not input.strip():
        return "JoyInside 输入为空。"

    bot_id = _joyinside_resolve_bot_id()
    token = _joyinside_get_token(bot_id=bot_id)
    request_id = str(uuid.uuid4())
    ws_session_id = f"{bot_id}_{session_id or uuid.uuid4().hex}"
    url = (
        f"{JOYINSIDE_WS_URL}?botId={bot_id}"
        f"&sessionId={ws_session_id}&requestId={request_id}"
    )

    ws = websocket.create_connection(
        url,
        header=[f"Authorization: Bearer {token}"],
        timeout=JOYINSIDE_TIMEOUT_SEC,
    )
    chunks: list[str] = []
    try:
        ws.send(
            json.dumps(
                {
                    "mid": str(uuid.uuid4()),
                    "contentType": "TEXT",
                    "uid": JOYINSIDE_UID,
                    "content": {"input": input.strip()},
                },
                ensure_ascii=False,
            )
        )

        start = time.time()
        while time.time() - start < JOYINSIDE_MAX_WAIT_SEC:
            raw = ws.recv()
            if isinstance(raw, bytes):
                continue

            message = json.loads(raw)
            content = message.get("content") or {}
            content_type = message.get("contentType")

            if message.get("code") not in (None, 200):
                raise RuntimeError(
                    f"JoyInside 下行错误: code={message.get('code')} msg={message.get('msg')}"
                )

            if content_type in {"AGENT", "ACTIVITY"}:
                text = content.get("content") or ""
                if text:
                    chunks.append(text)
                if content.get("finishReason") == "stop":
                    break

            if content_type == "EVENT":
                event_type = content.get("eventType")
                if event_type in {"COMPLETE", "EMPTY_CONTENT"}:
                    break
    finally:
        ws.close()

    text = "".join(chunks).strip()
    return text or "JoyInside 没有返回文本。"


# ========== MCP 工具 ==========

@mcp.tool()
async def list_agents() -> str:
    """列出所有已配置 agent 及其角色职责。在用户问"有哪些 agent"时调用。"""
    agents, source = _load_agent_registry()
    if not agents:
        return "未配置 agent。请在 CODEPOWER_AGENT_REGISTRY 中配置 agent 清单,或启用一个任务后端。"
    source_name = {
        "config": "配置",
        "builtin": "内置默认",
        "openclaw": "OpenClaw Gateway",
        "openclaw_lite": "OpenClaw Lite",
    }.get(source, source or "配置")
    lines = [f"{source_name} 共有 {len(agents)} 个 agent:"]
    for aid, a in agents.items():
        default_mark = "（默认）" if a.get("is_default") else ""
        workspace = f" · {a.get('workspace')}" if a.get("workspace") else ""
        lines.append(f"- {aid}{default_mark}: {a.get('role', '(无描述)')}{workspace}")
    return "\n".join(lines)


def _normalize_backend(backend: str) -> str:
    normalized = (backend or "").strip().lower().replace("-", "_")
    aliases = {
        "openclaw_gateway": "openclaw",
        "gateway": "openclaw",
        "claw": "openclaw",
        "lite": "openclaw_lite",
        "claude": "openclaw_lite",
        "claude_dispatch": "openclaw_lite",
    }
    return aliases.get(normalized, normalized)


def _resolve_agent_backends(requested: str = "") -> list[str]:
    enabled = [_normalize_backend(item) for item in AGENT_BACKENDS]
    primary = _normalize_backend(requested or AGENT_BACKEND or (enabled[0] if enabled else ""))
    if primary == "auto":
        primary = enabled[0] if enabled else ""
    if not primary:
        return []
    if requested:
        return [primary]
    backends = [primary]
    backends.extend(_normalize_backend(item) for item in AGENT_FALLBACK_BACKENDS)
    resolved: list[str] = []
    for item in backends:
        if not item or item in resolved:
            continue
        if enabled and item not in enabled:
            continue
        resolved.append(item)
    return resolved


def _resolve_agent_id(agent_id: str, agents: dict) -> tuple[str, str]:
    requested = (agent_id or "").strip()
    if requested in agents:
        return requested, ""
    if requested in {"", "main", "default", "默认", "主力"}:
        default_id = (AGENT_DEFAULT_ID or "").strip()
        if default_id and default_id in agents:
            return default_id, f"agent '{requested or 'default'}' 已映射到默认 agent '{default_id}'。"
        for aid, agent in agents.items():
            if agent.get("is_default"):
                return aid, f"agent '{requested or 'default'}' 已映射到默认 agent '{aid}'。"
        if len(agents) == 1:
            only_agent = next(iter(agents.keys()))
            return only_agent, f"agent '{requested or 'default'}' 已映射到唯一 agent '{only_agent}'。"
    return requested, ""


def _backend_display_name(backend: str, agent_id: str) -> tuple[str, str]:
    if backend == "openclaw":
        return "openclaw", f"OpenClaw {agent_id}"
    if backend == "hermes":
        return "hermes", f"Hermes {agent_id}"
    if backend == "openclaw_lite":
        return "openclaw_lite", f"OpenClaw Lite {agent_id}"
    return "dispatcher", f"{backend} {agent_id}"


async def _run_agent_backend(
    *,
    backend: str,
    agent_id: str,
    task: str,
    full_prompt: str,
    run_id: str,
) -> tuple[bool, str, str]:
    kind, display_name = _backend_display_name(backend, agent_id)
    worker_id = f"dispatch_{agent_id}_{backend}"
    _visual_start_worker(
        kind=kind,
        task=task,
        run_id=f"{run_id}_{backend}",
        worker_id=worker_id,
        display_name=display_name,
        agent_id=agent_id,
    )
    if backend == "openclaw":
        ok, result = await _run_openclaw_agent(
            agent_id,
            f"{task}\n\n请简短作答(150 字内),能直接被语音播报。",
            OPENCLAW_AGENT_TIMEOUT_SEC,
        )
    elif backend == "hermes":
        ok, result = await _run_hermes(full_prompt, HERMES_TIMEOUT_SEC)
    elif backend == "openclaw_lite":
        ok, result = await _run_claude_dispatch(agent_id, task, OPENCLAW_LITE_TIMEOUT_SEC)
    else:
        ok, result = False, f"未知 agent 后端: {backend}"
    _visual_finish_worker(
        run_id=f"{run_id}_{backend}",
        worker_id=worker_id,
        status="success" if ok else "failed",
        result=result,
    )
    return ok, result, backend


@mcp.tool()
async def list_agent_backends() -> str:
    """列出当前配置的任务执行后端。用户问"后端怎么配置"时调用。"""
    enabled = [_normalize_backend(item) for item in AGENT_BACKENDS]
    lines = [
        f"默认后端: {_normalize_backend(AGENT_BACKEND) or '未配置'}",
        f"启用后端: {', '.join(enabled) or '未配置'}",
        f"失败兜底: {', '.join(_normalize_backend(item) for item in AGENT_FALLBACK_BACKENDS) or '未启用'}",
        f"agent 清单: {'已配置' if AGENT_REGISTRY_CONFIG else '内置默认'}",
    ]
    if "openclaw" in enabled:
        lines.append(f"OpenClaw CLI: {OPENCLAW or 'MISSING'}")
        lines.append(f"OpenClaw Gateway: {OPENCLAW_GATEWAY_URL}")
    if "hermes" in enabled:
        lines.append(f"Hermes CLI: {HERMES if HERMES.exists() else 'MISSING'}")
    if "openclaw_lite" in enabled:
        lines.append(f"OpenClaw Lite dispatch.sh: {DISPATCH_SH if DISPATCH_SH.exists() else 'MISSING'}")
    return "\n".join(lines)


@mcp.tool()
async def dispatch_agent(agent_id: str, task: str, backend: str = "") -> str:
    """派发一个任务给指定 agent 执行。默认后端由 CODEPOWER_AGENT_BACKEND 配置。

    参数:
      agent_id: 已配置 agent id。先调用 list_agents 查看可用值。
      task: 任务描述(自然语言)。
      backend: 可选。为空时走 CODEPOWER_AGENT_BACKEND。

    返回: 执行结果文本(简短,可直接给用户听)
    """
    agents = _load_agents()
    if not agents:
        return "未配置 agent 清单。请设置 CODEPOWER_AGENT_REGISTRY,或启用能自动发现 agent 的任务后端。"
    agent_id, alias_note = _resolve_agent_id(agent_id, agents)
    if agent_id not in agents:
        return f"agent '{agent_id}' 不存在。可用: {', '.join(agents.keys())}"
    backends = _resolve_agent_backends(backend)
    if not backends:
        return "未配置任务后端。请设置 CODEPOWER_AGENT_BACKEND 或显式传入 backend。"

    run_id = f"run_{int(time.time())}"
    started = datetime.now().isoformat(timespec="seconds")
    role_prompt = _agent_role_prompt(agent_id)
    full_prompt = f"{role_prompt}\n\n任务: {task}\n\n请简短作答(150 字内),能直接被语音播报。"

    # 先记录派发
    state = {
        "run_id": run_id,
        "agent_id": agent_id,
        "task": task,
        "started": started,
        "status": "running",
        "backend": _normalize_backend(backend or AGENT_BACKEND),
    }
    _save_state(state)

    ok = False
    result = ""
    backend_used = ""
    failures: list[str] = []
    for candidate in backends:
        ok, result, backend_used = await _run_agent_backend(
            backend=candidate,
            agent_id=agent_id,
            task=task,
            full_prompt=full_prompt,
            run_id=run_id,
        )
        if ok:
            break
        failures.append(f"{candidate}: {result}")
    if not ok and failures:
        result = "\n".join(failures)

    finished = datetime.now().isoformat(timespec="seconds")
    state.update({
        "finished": finished,
        "status": "success" if ok else "failed",
        "backend": backend_used,
        "result": result[:2000],
        "alias_note": alias_note,
    })
    _save_state(state)
    # 持久化运行记录
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(state, ensure_ascii=False, indent=2))

    if ok:
        prefix_note = f"{alias_note}\n" if alias_note else ""
        return f"{prefix_note}[{backend_used} 已完成] {result}"
    else:
        return f"[派发失败] {result[:500]}"


async def _complete_openclaw_background(
    *,
    run_id: str,
    worker_id: str,
    agent_id: str,
    task: str,
    state: dict,
) -> None:
    ok, result = await _run_openclaw_agent(
        agent_id,
        f"{task}\n\n请简短作答(150 字内),能直接被语音播报。",
        OPENCLAW_AGENT_TIMEOUT_SEC,
    )
    finished = datetime.now().isoformat(timespec="seconds")
    state.update(
        {
            "finished": finished,
            "status": "success" if ok else "failed",
            "backend": "openclaw",
            "result": result[:2000],
        }
    )
    _persist_run_state(state)
    _visual_finish_worker(
        run_id=f"{run_id}_openclaw",
        worker_id=worker_id,
        status="success" if ok else "failed",
        result=result,
    )


@mcp.tool()
async def openclaw_agent_task(agent_id: str = "", task: str = "", wait: bool = False) -> str:
    """显式调用完整 OpenClaw Gateway 的 agent 执行任务。不是 OpenClaw Lite,也不走 Hermes。

    参数:
      agent_id: OpenClaw agent id。为空或 main/default 时映射到 CODEPOWER_OPENCLAW_DEFAULT_AGENT。
      task: 任务描述。
      wait: 是否同步等待 OpenClaw 结果。语音/小智场景默认 false,避免长任务阻塞连接。
    """
    agents = _load_openclaw_agents()
    if not agents:
        return "未找到完整 OpenClaw Gateway agent。请先确认 openclaw gateway 已运行,并且 openclaw agents list --json 可用。"
    resolved_agent_id, alias_note = _resolve_agent_id(agent_id, agents)
    if resolved_agent_id not in agents:
        return f"agent '{resolved_agent_id}' 不存在。可用: {', '.join(agents.keys())}"
    if not task.strip():
        return "OpenClaw 任务为空。"
    if wait:
        ok, result = await _run_openclaw_agent(
            resolved_agent_id,
            f"{task}\n\n请简短作答(150 字内),能直接被语音播报。",
            OPENCLAW_AGENT_TIMEOUT_SEC,
        )
        prefix = "[openclaw 已完成]" if ok else "[openclaw 失败]"
        return f"{prefix} {result}"

    run_id = f"run_{int(time.time())}"
    worker_id = f"dispatch_{resolved_agent_id}_openclaw"
    started = datetime.now().isoformat(timespec="seconds")
    state = {
        "run_id": run_id,
        "agent_id": resolved_agent_id,
        "task": task,
        "started": started,
        "status": "running",
        "backend": "openclaw",
        "async": True,
        "alias_note": alias_note,
    }
    _save_state(state)
    _visual_start_worker(
        kind="openclaw",
        task=task,
        run_id=f"{run_id}_openclaw",
        worker_id=worker_id,
        display_name=f"OpenClaw {resolved_agent_id}",
        agent_id=resolved_agent_id,
    )
    _track_background_task(
        asyncio.create_task(
            _complete_openclaw_background(
                run_id=run_id,
                worker_id=worker_id,
                agent_id=resolved_agent_id,
                task=task,
                state=state,
            )
        )
    )
    prefix_note = f"{alias_note}\n" if alias_note else ""
    return f"{prefix_note}[openclaw 已派发] {resolved_agent_id} 正在执行「{task[:80]}」。你可以稍后问“刚才那活儿进展”。"


@mcp.tool()
async def hermes_repo_task(task: str) -> str:
    """调用 Hermes 在专用工作目录执行通用工程任务。

    适用场景:
      - 用户明确说"让 Hermes/Hummus 做/改/查/生成"
      - 修改代码、分析仓库、生成文档、整理目录等工程任务

    参数:
      task: 直接描述要完成的任务，保留用户原始约束

    返回: Hermes 的简短执行结果摘要
    """
    try:
        WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        return f"[Hermes 失败] 工作目录不可用: {WORKSPACE_DIR} ({type(e).__name__}: {e})"

    run_id = f"hermes_{int(time.time())}"
    started = datetime.now().isoformat(timespec="seconds")
    full_prompt = (
        f"你正在工作目录 {WORKSPACE_DIR} 中处理真实任务。\n"
        "不要只给建议；如果任务要求执行、修改、整理、生成内容，就直接完成。\n"
        "先阅读相关文件或环境再动手，避免误改无关内容。\n"
        "完成后用简短中文总结结果；如果改了文件，带上文件路径；如果没改动，也直接说明原因。\n\n"
        f"任务: {task}"
    )

    state = {
        "run_id": run_id,
        "tool": "hermes_repo_task",
        "task": task,
        "started": started,
        "status": "running",
        "backend": "hermes",
        "workspace": str(WORKSPACE_DIR),
    }
    _save_state(state)
    _visual_start_worker(
        kind="hermes",
        task=task,
        run_id=run_id,
        worker_id="hermes_repo",
        display_name="Hermes repo",
        workspace=str(WORKSPACE_DIR),
    )

    try:
        ok, result = await _run_hermes(
            full_prompt, HERMES_REPO_TIMEOUT_SEC, cwd=WORKSPACE_DIR
        )
    except asyncio.CancelledError:
        ok, result = False, "Hermes 调用被上游连接取消"
    finished = datetime.now().isoformat(timespec="seconds")
    state.update(
        {
            "finished": finished,
            "status": "success" if ok else "failed",
            "result": result[:4000],
        }
    )
    _save_state(state)
    _visual_finish_worker(
        run_id=run_id,
        worker_id="hermes_repo",
        status="success" if ok else "failed",
        result=result,
    )
    (RUNS_DIR / f"{run_id}.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2)
    )

    if ok:
        return f"[hermes 已完成] {result}"
    return f"[Hermes 失败] {result[:500]}"


# joyinside_chat 工具已移至 xiaozhi-server 的 JoyInsideLLM provider（闲聊模式）
# 不再通过 MCP dispatcher 调用


@mcp.tool()
async def send_email(to: str, subject: str, body: str) -> str:
    """给预置联系人发送邮件。GPT 负责起草邮件标题和正文。

    参数:
      to: 联系人名字（如"罗总""黄老师"），会自动匹配邮箱地址
      subject: 邮件标题
      body: 邮件正文

    返回: 发送结果
    """
    run_id = f"email_{int(time.time())}"
    _visual_start_worker(
        kind="email",
        task=f"send email to {to}: {subject}",
        run_id=run_id,
        worker_id="send_email",
        display_name="Email",
    )
    if not RESEND_API_KEY:
        _visual_finish_worker(
            run_id=run_id,
            worker_id="send_email",
            status="failed",
            result="Resend API Key 未配置，无法发送邮件。",
        )
        return "Resend API Key 未配置，无法发送邮件。"

    # 匹配联系人
    email = RESEND_CONTACTS.get(to)
    if not email:
        # 模糊匹配
        for name, addr in RESEND_CONTACTS.items():
            if to in name or name in to:
                email = addr
                break
    if not email:
        available = "、".join(RESEND_CONTACTS.keys()) or "无"
        result = f"找不到联系人「{to}」。已绑定的联系人：{available}"
        _visual_finish_worker(
            run_id=run_id,
            worker_id="send_email",
            status="failed",
            result=result,
        )
        return result

    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": f"{RESEND_FROM_NAME} <{RESEND_FROM_EMAIL}>",
                "to": [email],
                "subject": subject,
                "text": body,
            },
            timeout=15,
        )
        if resp.status_code in (200, 201):
            result = f"邮件已发送给{to}（{email}），主题：{subject}"
            _visual_finish_worker(
                run_id=run_id,
                worker_id="send_email",
                status="success",
                result=result,
            )
            return result
        else:
            result = f"邮件发送失败：{resp.status_code} {resp.text[:200]}"
            _visual_finish_worker(
                run_id=run_id,
                worker_id="send_email",
                status="failed",
                result=result,
            )
            return result
    except Exception as e:
        result = f"邮件发送异常：{type(e).__name__}: {e}"
        _visual_finish_worker(
            run_id=run_id,
            worker_id="send_email",
            status="failed",
            result=result,
        )
        return result


@mcp.tool()
async def query_agent_status(tool: str = "", recent: int = 1) -> str:
    """查询任务执行状态。

    参数:
      tool: 按工具类型筛选。可选值："openclaw"、"hermes"、"claude"、"codex"、"dispatch"、"email"。
            为空则不筛选。用户说"OpenClaw 那个任务"时传 "openclaw"，说"Hermes那个任务"时传 "hermes"。
      recent: 返回最近几条记录，默认1条。用户说"最近的任务都有啥"时可设为3~5。

    返回: 任务状态和结果摘要
    """
    # 工具类型 → run_id 前缀映射。dispatch_agent 的 run_id 都是 run_*,
    # openclaw/hermes 这类后端需要再看 state.backend,避免互相串结果。
    tool_prefix = {
        "openclaw": "run_",
        "hermes": "hermes_",
        "claude": "claude_",
        "codex": "codex_",
        "dispatch": "run_",
        "email": None,  # send_email 不生成 run 记录
    }

    # 读所有 run 记录，按时间倒序
    runs = sorted(RUNS_DIR.glob("*.json"), key=lambda f: f.stat().st_mtime, reverse=True)
    if not runs:
        # 兜底读 state file
        state = _load_state()
        if state:
            return _format_status(state)
        return "最近没有派发过任务。"

    # 筛选
    results = []
    prefix = tool_prefix.get(tool, tool) if tool else ""
    for run_file in runs:
        if prefix and not run_file.stem.startswith(prefix):
            continue
        try:
            state = json.loads(run_file.read_text())
            if tool in {"openclaw", "hermes", "openclaw_lite"}:
                backend = str(state.get("backend") or "")
                direct_tool = str(state.get("tool") or "")
                if backend != tool and not direct_tool.startswith(tool):
                    continue
            results.append(_format_status(state))
        except Exception:
            continue
        if len(results) >= recent:
            break

    if not results:
        if tool:
            return f"最近没有 {tool} 相关的任务记录。"
        return "最近没有派发过任务。"

    return "\n---\n".join(results)


def _format_status(state: dict) -> str:
    """格式化任务状态为可读文本"""
    run_id = state.get("run_id", "?")
    tool = state.get("tool") or state.get("agent_id") or "?"
    status = state.get("status", "?")
    task = state.get("task", "")[:80]
    backend = state.get("backend", "?")
    started = state.get("started", "")

    if status == "running":
        try:
            elapsed = int((datetime.now() - datetime.fromisoformat(started)).total_seconds())
        except Exception:
            elapsed = 0
        return f"[{run_id}] {tool} 正在执行「{task}」，已耗时 {elapsed} 秒"

    if status == "success":
        result = state.get("result", "")
        return f"[{run_id}] {tool} 已完成（后端: {backend}）。结果: {result[:400]}"

    return f"[{run_id}] {tool} 执行{status}: {state.get('result', '')[:400]}"


@mcp.tool()
async def read_daily_report(date: str = "today") -> str:
    """读取 OpenClaw 日报。在用户问"今天日报""昨天做了什么"时调用。

    参数:
      date: "today" / "yesterday" / "YYYY-MM-DD"
    """
    if date == "today":
        d = datetime.now().strftime("%Y-%m-%d")
    elif date == "yesterday":
        d = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        d = date

    report = DAILY_LOG_DIR / f"{d}.md"
    if not report.exists():
        # 找最近一份作为退路
        candidates = sorted(DAILY_LOG_DIR.glob("*.md"), reverse=True)
        if not candidates:
            return f"日报目录为空 ({DAILY_LOG_DIR})"
        report = candidates[0]
        fallback_note = f"(未找到 {d} 日报,改读最新的 {report.stem})\n"
    else:
        fallback_note = ""

    text = report.read_text(encoding="utf-8", errors="replace")
    # 语音场景,截断到 800 字
    if len(text) > 800:
        text = text[:800] + "...(日报较长,以上是开头)"
    return fallback_note + text


@mcp.tool()
async def run_codex(task: str, workdir: str = "", allow_edits: bool = False) -> str:
    """调用本机 Codex CLI 执行代码任务。默认只读分析；只有用户明确要求修改代码时才把 allow_edits 设为 true。

    参数:
      task: 交给 Codex 的自然语言任务
      workdir: 工作目录，默认使用 dispatcher 当前目录
      allow_edits: 是否允许 Codex 修改工作区。默认 false，只读。

    返回: Codex 最终输出摘要
    """
    if not CODEX:
        return "Codex CLI 未安装或不在 PATH 中。"
    cwd = _resolve_workdir(workdir)
    if not cwd.exists():
        return f"工作目录不存在: {cwd}"

    run_id = f"codex_{int(time.time())}"
    started = datetime.now().isoformat(timespec="seconds")
    state = {"run_id": run_id, "tool": "run_codex", "task": task, "started": started, "status": "running", "backend": "codex", "workspace": str(cwd)}
    _save_state(state)
    _visual_start_worker(
        kind="codex",
        task=task,
        run_id=run_id,
        worker_id="codex",
        display_name="Codex",
        workspace=str(cwd),
    )
    with tempfile.NamedTemporaryFile(prefix="codex-last-", suffix=".txt", delete=False) as tmp:
        output_path = Path(tmp.name)
    try:
        cmd = [
            CODEX,
            "exec",
            "--cd",
            str(cwd),
            "--skip-git-repo-check",
            "--color",
            "never",
            "--output-last-message",
            str(output_path),
            "-c",
            "model_reasoning_effort=\"low\"",
        ]
        if allow_edits:
            cmd += ["--full-auto"]
        else:
            cmd += ["--sandbox", "read-only"]
        cmd.append(task)

        ok, result = await _run_command(cmd, CODEX_TIMEOUT_SEC, cwd)
        if output_path.exists():
            final_text = output_path.read_text(encoding="utf-8", errors="replace").strip()
            if final_text:
                result = final_text
    finally:
        try:
            output_path.unlink(missing_ok=True)
        except Exception:
            pass
    finished = datetime.now().isoformat(timespec="seconds")
    state.update({"finished": finished, "status": "success" if ok else "failed", "result": result[:4000]})
    _save_state(state)
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(state, ensure_ascii=False, indent=2))

    prefix = "[Codex 已完成]" if ok else "[Codex 失败]"
    _visual_finish_worker(
        run_id=run_id,
        worker_id="codex",
        status="success" if ok else "failed",
        result=result,
    )
    return f"{prefix} {result[:2000]}"


@mcp.tool()
async def run_claude_code(task: str, workdir: str = "", allow_edits: bool = False, resume: bool = False) -> str:
    """调用本机 Claude Code 执行代码任务。默认只读分析；只有用户明确要求修改代码时才把 allow_edits 设为 true。

    参数:
      task: 交给 Claude Code 的自然语言任务
      workdir: 工作目录，默认使用 dispatcher 当前目录
      allow_edits: 是否允许 Claude Code 修改工作区。默认 false，只读。
      resume: 是否继续上一次的会话。用户追问上次任务的结果、要求修改上次的产出、或说"继续""接着上次"时设为 true；全新任务设为 false。

    返回: Claude Code 最终输出摘要
    """
    if not CLAUDE:
        return "Claude Code CLI 未安装或不在 PATH 中。"
    cwd = _resolve_workdir(workdir)
    if not cwd.exists():
        return f"工作目录不存在: {cwd}"

    run_id = f"claude_{int(time.time())}"
    started = datetime.now().isoformat(timespec="seconds")
    state = {"run_id": run_id, "tool": "run_claude_code", "task": task, "started": started, "status": "running", "backend": "claude_code", "workspace": str(cwd), "resume": resume}
    _save_state(state)
    _visual_start_worker(
        kind="claude_code",
        task=task,
        run_id=run_id,
        worker_id="claude_code",
        display_name="Claude Code",
        workspace=str(cwd),
    )
    cmd = [
        CLAUDE,
        "-p",
        task,
        "--output-format",
        "text",
    ]
    if resume:
        cmd += ["--resume"]
    if allow_edits:
        cmd += ["--permission-mode", "acceptEdits"]
    else:
        cmd += ["--allowedTools", "Read,Grep,Glob,LS"]

    ok, result = await _run_command(cmd, CLAUDE_CODE_TIMEOUT_SEC, cwd)
    finished = datetime.now().isoformat(timespec="seconds")
    state.update({"finished": finished, "status": "success" if ok else "failed", "result": result[:4000]})
    _save_state(state)
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(state, ensure_ascii=False, indent=2))

    prefix = "[Claude Code 已完成]" if ok else "[Claude Code 失败]"
    _visual_finish_worker(
        run_id=run_id,
        worker_id="claude_code",
        status="success" if ok else "failed",
        result=result,
    )
    return f"{prefix} {result[:2000]}"


# ========== 启动 ==========

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9000"))
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[dispatcher] MCP streamable-http on 0.0.0.0:{port}/mcp")
    enabled = [_normalize_backend(item) for item in AGENT_BACKENDS]
    if AGENT_REGISTRY_CONFIG:
        agents = _load_configured_agents()
        print(f"[dispatcher] agents(config): {list(agents.keys())}")
    else:
        print("[dispatcher] agents: not configured")
    print(f"[dispatcher] agent backend default: {_normalize_backend(AGENT_BACKEND) or 'not configured'}")
    print(f"[dispatcher] agent backends enabled: {', '.join(enabled) or 'not configured'}")
    if "openclaw" in enabled:
        print(f"[dispatcher] openclaw: {OPENCLAW or 'MISSING'}")
        print(f"[dispatcher] openclaw gateway: {OPENCLAW_GATEWAY_URL}")
    if "hermes" in enabled:
        print(f"[dispatcher] hermes: {HERMES} ({'ok' if HERMES.exists() else 'MISSING'})")
        print(f"[dispatcher] hermes workspace: {WORKSPACE_DIR}")
    if "openclaw_lite" in enabled:
        print(f"[dispatcher] openclaw lite dispatch.sh: {DISPATCH_SH} ({'ok' if DISPATCH_SH.exists() else 'MISSING'})")
    print(f"[dispatcher] codex: {CODEX or 'MISSING'}")
    print(f"[dispatcher] claude: {CLAUDE or 'MISSING'}")
    # FastMCP streamable-http 默认路径 /mcp,端口通过 settings
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
