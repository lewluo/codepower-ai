"""
OpenClaw Dispatcher — 小智语音的后端工具服务
架构: 小智(Docker) → streamable-http MCP → 本服务(host:9000) → Hermes/OpenClaw

工具:
  list_agents()                    - 列出可用 agent
  dispatch_agent(agent_id, task)   - 派发任务(Hermes 主路, Claude 兜底)
  query_agent_status()             - 查询最近一次派发状态
  read_daily_report(date='today')  - 读 OpenClaw 日报
  hermes_repo_task(task)           - 调 Hermes 在专用工作目录执行仓库任务
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
import tempfile
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

import requests
import websocket
from mcp.server.fastmcp import FastMCP

HOME = Path.home()
AGENTS_JSON = HOME / ".openclaw/lite/agents.json"
DISPATCH_SH = HOME / ".openclaw/lite/bin/dispatch.sh"
DAILY_LOG_DIR = HOME / ".openclaw/workspace/logs/daily"
HERMES = HOME / ".local/bin/hermes"
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

HERMES_TIMEOUT_SEC = 45          # 语音场景下不要太长,保证"声音在说"的体感
HERMES_REPO_TIMEOUT_SEC = 300
CLAUDE_FALLBACK_TIMEOUT_SEC = 120
CODEX_TIMEOUT_SEC = 180
CLAUDE_CODE_TIMEOUT_SEC = 180
JOYINSIDE_TIMEOUT_SEC = 20
JOYINSIDE_MAX_WAIT_SEC = 60

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

mcp = FastMCP("openclaw-dispatcher")


def _load_agents() -> dict:
    if not AGENTS_JSON.exists():
        return {}
    with AGENTS_JSON.open() as f:
        return json.load(f).get("agents", {})


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


async def _run_hermes(
    task_prompt: str, timeout: int, cwd: Optional[Path] = None
) -> tuple[bool, str]:
    """调 Hermes 非交互模式,返回 (成功, 结果文本)"""
    if not HERMES.exists():
        return False, "Hermes 未安装"
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
            return False, f"Hermes exit={proc.returncode}: {err.decode('utf-8', errors='replace')[:500]}"
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
    except Exception as e:
        return False, f"Hermes 异常: {type(e).__name__}: {e}"


async def _run_claude_dispatch(agent_id: str, task: str, timeout: int) -> tuple[bool, str]:
    """调 OpenClaw dispatch.sh(claude -p 兜底),返回 (成功, 结果文本)"""
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
    """列出所有可用的 OpenClaw agent 及其角色职责。在用户问"有哪些 agent"时调用。"""
    agents = _load_agents()
    if not agents:
        return "未找到 agent 注册表(~/.openclaw/lite/agents.json 不存在)"
    lines = [f"共有 {len(agents)} 个 agent:"]
    for aid, a in agents.items():
        lines.append(f"- {aid}: {a.get('role', '(无描述)')}")
    return "\n".join(lines)


@mcp.tool()
async def dispatch_agent(agent_id: str, task: str) -> str:
    """派发一个任务给指定 agent 执行。
    优先走 Hermes(gpt-5.4,免费快速),Hermes 失败自动回落 OpenClaw(Claude,更强但有费用)。

    参数:
      agent_id: 必须是以下之一 — main, planner, site-ops, support, overseas-dev, designer, keyword-miner
      task: 任务描述(自然语言,例如"查今天日报" / "看看 bazi 站点状态")

    返回: 执行结果文本(简短,可直接给用户听)
    """
    agents = _load_agents()
    if agent_id not in agents:
        return f"agent '{agent_id}' 不存在。可用: {', '.join(agents.keys())}"

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
        "backend": "hermes",
    }
    _save_state(state)

    # 主路: Hermes
    ok, result = await _run_hermes(full_prompt, HERMES_TIMEOUT_SEC)
    backend_used = "hermes"

    if not ok:
        # 兜底: Claude via OpenClaw
        ok2, result2 = await _run_claude_dispatch(agent_id, task, CLAUDE_FALLBACK_TIMEOUT_SEC)
        if ok2:
            result = result2
            ok = True
            backend_used = "claude"
        else:
            result = f"主路 Hermes 失败: {result}\n兜底 Claude 也失败: {result2}"

    finished = datetime.now().isoformat(timespec="seconds")
    state.update({
        "finished": finished,
        "status": "success" if ok else "failed",
        "backend": backend_used,
        "result": result[:2000],
    })
    _save_state(state)
    # 持久化运行记录
    (RUNS_DIR / f"{run_id}.json").write_text(json.dumps(state, ensure_ascii=False, indent=2))

    if ok:
        return f"[{backend_used} 已完成] {result}"
    else:
        return f"[派发失败] {result[:500]}"


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

    ok, result = await _run_hermes(
        full_prompt, HERMES_REPO_TIMEOUT_SEC, cwd=WORKSPACE_DIR
    )
    finished = datetime.now().isoformat(timespec="seconds")
    state.update(
        {
            "finished": finished,
            "status": "success" if ok else "failed",
            "result": result[:4000],
        }
    )
    _save_state(state)
    (RUNS_DIR / f"{run_id}.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2)
    )

    if ok:
        return f"[hermes 已完成] {result}"
    return f"[Hermes 失败] {result[:500]}"


@mcp.tool()
async def joyinside_chat(input: str, session_id: str = "codepower-tool") -> str:
    """调用 JoyInside 智能体的文本对话能力。

    适用场景:
      - 用户明确说"用 JoyInside"、"调用 JoyInside"
      - 玩游戏、讲故事、电子宠物、宝可梦、小马宝莉等 JoyInside bot 支持的陪伴/互动能力

    参数:
      input: 交给 JoyInside 智能体的原始用户请求
      session_id: 可选会话 ID，相同 ID 可维持 JoyInside 多轮上下文

    返回: JoyInside 智能体返回的文本
    """
    try:
        return await asyncio.to_thread(_joyinside_chat_sync, input, session_id)
    except Exception as e:
        return f"[JoyInside 失败] {type(e).__name__}: {e}"


@mcp.tool()
async def query_agent_status() -> str:
    """查询最近一次派发任务的执行状态。在用户问"刚才那个任务好了吗"时调用。"""
    state = _load_state()
    if not state:
        return "最近没有派发过任务。"
    agent_id = state.get("agent_id", "?")
    status = state.get("status", "?")
    task = state.get("task", "")[:80]
    backend = state.get("backend", "?")
    started = state.get("started", "")

    if status == "running":
        try:
            elapsed = int((datetime.now() - datetime.fromisoformat(started)).total_seconds())
        except Exception:
            elapsed = 0
        return f"{agent_id} 正在执行 {task},已耗时 {elapsed} 秒"

    if status == "success":
        result = state.get("result", "")
        return f"{agent_id} 已完成(后端: {backend})。结果: {result[:400]}"

    return f"{agent_id} 执行{status}:{state.get('result', '')[:400]}"


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
    prefix = "[Codex 已完成]" if ok else "[Codex 失败]"
    return f"{prefix} {result[:2000]}"


@mcp.tool()
async def run_claude_code(task: str, workdir: str = "", allow_edits: bool = False) -> str:
    """调用本机 Claude Code 执行代码任务。默认只读分析；只有用户明确要求修改代码时才把 allow_edits 设为 true。

    参数:
      task: 交给 Claude Code 的自然语言任务
      workdir: 工作目录，默认使用 dispatcher 当前目录
      allow_edits: 是否允许 Claude Code 修改工作区。默认 false，只读。

    返回: Claude Code 最终输出摘要
    """
    if not CLAUDE:
        return "Claude Code CLI 未安装或不在 PATH 中。"
    cwd = _resolve_workdir(workdir)
    if not cwd.exists():
        return f"工作目录不存在: {cwd}"

    cmd = [
        CLAUDE,
        "-p",
        task,
        "--output-format",
        "text",
        "--no-session-persistence",
    ]
    if allow_edits:
        cmd += ["--permission-mode", "acceptEdits"]
    else:
        cmd += ["--allowedTools", "Read,Grep,Glob,LS"]

    ok, result = await _run_command(cmd, CLAUDE_CODE_TIMEOUT_SEC, cwd)
    prefix = "[Claude Code 已完成]" if ok else "[Claude Code 失败]"
    return f"{prefix} {result[:2000]}"


# ========== 启动 ==========

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9000"))
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[dispatcher] MCP streamable-http on 0.0.0.0:{port}/mcp")
    print(f"[dispatcher] agents: {list(_load_agents().keys())}")
    print(f"[dispatcher] hermes: {HERMES} ({'ok' if HERMES.exists() else 'MISSING'})")
    print(f"[dispatcher] hermes workspace: {WORKSPACE_DIR}")
    print(f"[dispatcher] dispatch.sh: {DISPATCH_SH} ({'ok' if DISPATCH_SH.exists() else 'MISSING'})")
    print(f"[dispatcher] codex: {CODEX or 'MISSING'}")
    print(f"[dispatcher] claude: {CLAUDE or 'MISSING'}")
    # FastMCP streamable-http 默认路径 /mcp,端口通过 settings
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
