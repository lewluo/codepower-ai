"""
OpenClaw Dispatcher — 小智语音的后端工具服务
架构: 小智(Docker) → streamable-http MCP → 本服务(host:9000) → Hermes/OpenClaw

工具:
  hermes_repo_task(task)           - 直接调用 Hermes 处理通用任务
"""
from __future__ import annotations

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from mcp.server.fastmcp import FastMCP

HOME = Path.home()
AGENTS_JSON = HOME / ".openclaw/lite/agents.json"
DISPATCH_SH = HOME / ".openclaw/lite/bin/dispatch.sh"
DAILY_LOG_DIR = HOME / ".openclaw/workspace/logs/daily"
HERMES = HOME / ".local/bin/hermes"
WORKSPACE_DIR = Path("/Users/carlos_chen/Desktop/work_space/hemers_work_dir")

STATE_FILE = Path("/tmp/xiaozhi-dispatcher-state.json")
RUNS_DIR = Path("/tmp/xiaozhi-dispatcher-runs")
RUNS_DIR.mkdir(exist_ok=True)

HERMES_TIMEOUT_SEC = 300         # 与 xiaozhi 的 tool_call_timeout 保持一致
CLAUDE_FALLBACK_TIMEOUT_SEC = 120

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


async def _run_hermes(task_prompt: str, timeout: int) -> tuple[bool, str]:
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
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=str(WORKSPACE_DIR),
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


# ========== MCP 工具 ==========

async def list_agents() -> str:
    """列出所有可用的 OpenClaw agent 及其角色职责。在用户问"有哪些 agent"时调用。"""
    agents = _load_agents()
    if not agents:
        return "未找到 agent 注册表(~/.openclaw/lite/agents.json 不存在)"
    lines = [f"共有 {len(agents)} 个 agent:"]
    for aid, a in agents.items():
        lines.append(f"- {aid}: {a.get('role', '(无描述)')}")
    return "\n".join(lines)


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
    """直接调用 Hermes 在当前工作目录内执行通用任务。

    适用场景:
      - 修改代码 / 修 bug / 实现功能 / 分析仓库
      - 读取文件 / 组织目录 / 生成文档 / 执行通用工程任务
      - 任何明确交给 Hermes 处理的工作

    参数:
      task: 直接描述要在当前工作目录完成的任务

    返回: Hermes 的简短执行结果摘要
    """
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

    ok, result = await _run_hermes(full_prompt, HERMES_TIMEOUT_SEC)
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


# ========== 启动 ==========

if __name__ == "__main__":
    port = int(os.environ.get("PORT", "9000"))
    WORKSPACE_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[dispatcher] MCP streamable-http on 0.0.0.0:{port}/mcp")
    print(f"[dispatcher] workspace: {WORKSPACE_DIR}")
    print(f"[dispatcher] agents: {list(_load_agents().keys())}")
    print(f"[dispatcher] hermes: {HERMES} ({'ok' if HERMES.exists() else 'MISSING'})")
    print(f"[dispatcher] dispatch.sh: {DISPATCH_SH} ({'ok' if DISPATCH_SH.exists() else 'MISSING'})")
    # FastMCP streamable-http 默认路径 /mcp,端口通过 settings
    mcp.settings.host = "0.0.0.0"
    mcp.settings.port = port
    mcp.run(transport="streamable-http")
