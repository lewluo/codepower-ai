from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, AsyncIterator

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, StreamingResponse
from starlette.routing import Route

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from dispatcher.server import (  # noqa: E402
    dispatch_agent,
    list_agents,
    list_agent_backends,
    hermes_repo_task,
    openclaw_agent_task,
    query_agent_status,
    read_daily_report,
)

SERVICE_TOKEN = os.environ.get("JOYINSIDE_SERVICE_TOKEN", "")
DEFAULT_AGENT_ID = os.environ.get("CODEPOWER_DEFAULT_AGENT") or "planner"
AGENT_ALIASES = {
    "planner": ["planner", "规划分身", "规划师", "调度分身", "默认分身", "主任务"],
    "executor": ["executor", "执行分身", "执行器", "执行同事"],
}
DIRECT_HERMES_ALIAS_RE = re.compile(r"(hermes|hummus|赫尔墨斯|赫耳墨斯)", re.IGNORECASE)
DIRECT_OPENCLAW_ALIAS_RE = re.compile(r"(open\s*claw|openclaw|欧喷克劳)", re.IGNORECASE)


def _authorized(request: Request) -> bool:
    if not SERVICE_TOKEN:
        return True
    auth = request.headers.get("authorization", "")
    query_token = request.query_params.get("token", "")
    expected = SERVICE_TOKEN
    return auth in {expected, f"Bearer {expected}"} or query_token == expected


def _extract_parameters(body: dict[str, Any]) -> dict[str, Any]:
    params = body.get("parameters")
    if isinstance(params, dict):
        return params
    return {}


def _input_text(params: dict[str, Any]) -> str:
    value = params.get("input")
    if isinstance(value, str):
        return value.strip()
    messages = params.get("messages")
    if isinstance(messages, list):
        for message in reversed(messages):
            if isinstance(message, dict) and message.get("role") == "user":
                content = message.get("content")
                if isinstance(content, str):
                    return content.strip()
    return ""


def _infer_tool(text: str, explicit: str | None) -> str:
    if explicit:
        return explicit
    lowered = text.lower()
    if any(word in text for word in ["有哪些", "能派谁", "可用", "分身"]) or "agent" in lowered:
        return "list_agents"
    if any(word in text for word in ["后端", "backends", "backend"]):
        return "list_agent_backends"
    if any(word in text for word in ["日报", "今天干了啥", "昨天干了啥"]):
        return "read_daily_report"
    if any(word in text for word in ["刚才", "好了没", "搞定", "状态", "进展"]):
        return "query_agent_status"
    if DIRECT_HERMES_ALIAS_RE.search(text):
        return "hermes_repo_task"
    if DIRECT_OPENCLAW_ALIAS_RE.search(text):
        return "openclaw_agent_task"
    return "dispatch_agent"


def _infer_date(text: str, params: dict[str, Any]) -> str:
    date = params.get("date")
    if isinstance(date, str) and date:
        return date
    if "昨天" in text:
        return "yesterday"
    match = re.search(r"\d{4}-\d{2}-\d{2}", text)
    if match:
        return match.group(0)
    return "today"


def _infer_agent_and_task(text: str, params: dict[str, Any]) -> tuple[str, str]:
    agent_id = params.get("agent_id")
    if not isinstance(agent_id, str) or not agent_id:
        lowered = text.lower()
        agent_id = DEFAULT_AGENT_ID
        for candidate, aliases in AGENT_ALIASES.items():
            if any(alias in lowered or alias in text for alias in aliases):
                agent_id = candidate
                break

    task = params.get("task")
    if not isinstance(task, str) or not task:
        task = text
        for aliases in AGENT_ALIASES.values():
            for alias in aliases:
                task = re.sub(re.escape(alias), "", task, flags=re.IGNORECASE)
        task = re.sub(r"^(个|一个)?(任务|活儿|活)\s*", "", task, flags=re.IGNORECASE)
        task = task.lstrip(" ，,。")
        task = re.sub(
            r"^(请)?(你)?(帮我)?(派|安排|分配|让|叫|交给|麻烦|去|做|查|看)+",
            "",
            task,
            flags=re.IGNORECASE,
        ).strip(" ，,。")
    return agent_id, task or text or "请处理用户请求。"


def _strip_backend_alias(task: str, pattern: re.Pattern[str]) -> str:
    return re.sub(pattern, "", task, count=1).strip(" ，,。") or task


async def _run_tool(tool: str, params: dict[str, Any]) -> str:
    text = _input_text(params)
    if tool == "list_agents":
        return await list_agents()
    if tool == "list_agent_backends":
        return await list_agent_backends()
    if tool == "read_daily_report":
        return await read_daily_report(_infer_date(text, params))
    if tool == "query_agent_status":
        return await query_agent_status()
    if tool == "dispatch_agent":
        agent_id, task = _infer_agent_and_task(text, params)
        return await dispatch_agent(agent_id, task)
    if tool == "hermes_repo_task":
        _, task = _infer_agent_and_task(text, params)
        task = _strip_backend_alias(task, DIRECT_HERMES_ALIAS_RE)
        return await hermes_repo_task(task)
    if tool == "openclaw_agent_task":
        agent_id, task = _infer_agent_and_task(text, params)
        task = _strip_backend_alias(task, DIRECT_OPENCLAW_ALIAS_RE)
        return await openclaw_agent_task(agent_id, task)
    return f"未知工具: {tool}"


def _sse(event_id: int, event: str, data: dict[str, Any]) -> str:
    return f"id: {event_id}\nevent: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


async def _message_stream(text: str) -> AsyncIterator[str]:
    yield _sse(
        0,
        "Message",
        {
            "content": text,
            "node_title": "Message",
            "node_seq_id": "0",
            "node_is_finish": True,
        },
    )
    yield _sse(1, "Done", {})


async def health(_: Request) -> JSONResponse:
    return JSONResponse({"ok": True, "service": "joyinside-gateway"})


async def skill(request: Request) -> StreamingResponse | JSONResponse:
    if not _authorized(request):
        return JSONResponse({"error": "unauthorized"}, status_code=401)
    try:
        body = await request.json()
    except Exception:
        body = {}
    params = _extract_parameters(body)
    tool = _infer_tool(_input_text(params), request.query_params.get("tool"))
    try:
        text = await asyncio.wait_for(_run_tool(tool, params), timeout=120)
    except Exception as exc:
        text = f"技能执行失败: {type(exc).__name__}: {exc}"
    return StreamingResponse(_message_stream(text), media_type="text/event-stream")


app = Starlette(
    routes=[
        Route("/health", health, methods=["GET"]),
        Route("/joyinside/skill", skill, methods=["POST"]),
    ]
)


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "9100"))
    uvicorn.run(app, host="0.0.0.0", port=port)
