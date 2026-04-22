import json
import uuid
import asyncio
import time
from typing import TYPE_CHECKING, Any, Dict

from core.handle.sendAudioHandle import send_proposal_message
from core.handle.reportHandle import enqueue_tool_report
from core.providers.tts.dto.dto import ContentType, TTSMessageDTO, SentenceType
from core.utils.dialogue import Message
from plugins_func.register import Action, ActionResponse

if TYPE_CHECKING:
    from core.connection import ConnectionHandler

TAG = __name__

# 只读/查询类工具不需要用户确认，直接执行
_READONLY_TOOLS = {
    "query_agent_status",
    "list_agents",
    "read_daily_report",
    "get_lunar",
    "self_get_device_status",
}


def is_decision_tool(function_name: str) -> bool:
    """判断工具是否需要用户确认。只读查询类工具不需要。"""
    return function_name not in _READONLY_TOOLS


def _load_arguments(arguments: Any) -> Dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        try:
            return json.loads(arguments) if arguments else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _dump_arguments(arguments: Any) -> str:
    if isinstance(arguments, str):
        return arguments
    return json.dumps(arguments or {}, ensure_ascii=False)


_TOOL_DISPLAY = {
    "hermes_repo_task": "Hermes",
    "dispatch_agent": "分身派发",
    "list_agents": "查看分身",
    "query_agent_status": "查询进度",
    "read_daily_report": "读日报",
    "run_codex": "Codex",
    "run_claude_code": "Claude Code",
    "send_email": "发送邮件",
}


def _build_proposal_text(function_name: str, arguments: Dict[str, Any]) -> str:
    display = _TOOL_DISPLAY.get(function_name, function_name)
    task = arguments.get("task") or arguments.get("input") or arguments.get("date") or ""
    if task:
        return f"方案：用{display}处理「{task}」。采纳还是拒绝？"
    return f"方案：调用{display}。采纳还是拒绝？"


def _display_tool_name(function_name: str | None) -> str:
    return _TOOL_DISPLAY.get(function_name, function_name or "待确认操作")


async def stage_pending_proposal(
    conn: "ConnectionHandler",
    function_call_data: Dict[str, Any],
    original_text: str,
) -> bool:
    function_name = function_call_data.get("name")
    if not is_decision_tool(function_name):
        return False

    arguments = _load_arguments(function_call_data.get("arguments"))
    proposal_text = _build_proposal_text(function_name, arguments)
    function_call_data = {
        "name": function_name,
        "id": function_call_data.get("id") or str(uuid.uuid4().hex),
        "arguments": _dump_arguments(arguments),
    }

    conn.pending_proposal = {
        "function_name": function_name,
        "function_call_data": function_call_data,
        "agent_id": arguments.get("agent_id"),
        "task": arguments.get("task"),
        "proposal_text": proposal_text,
        "original_text": original_text,
    }
    conn.logger.bind(tag=TAG).info(f"已创建待确认 proposal: {conn.pending_proposal}")

    conn.dialogue.put(Message(role="user", content=original_text))
    await send_proposal_message(
        conn,
        "pending",
        {
            "function_name": _display_tool_name(function_name),
            "proposal_text": proposal_text,
            "task": arguments.get("task"),
        },
    )
    _speak_text(conn, proposal_text)
    return True


def _prepare_tts_round(conn: "ConnectionHandler"):
    conn.sentence_id = str(uuid.uuid4().hex)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.FIRST,
            content_type=ContentType.ACTION,
        )
    )


def _finish_tts_round(conn: "ConnectionHandler"):
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.LAST,
            content_type=ContentType.ACTION,
        )
    )


def _speak_text(conn: "ConnectionHandler", text: str):
    conn.tts.store_tts_text(conn.sentence_id, text)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.FIRST,
            content_type=ContentType.ACTION,
        )
    )
    conn.tts.tts_one_sentence(conn, ContentType.TEXT, content_detail=text)
    conn.tts.tts_text_queue.put(
        TTSMessageDTO(
            sentence_id=conn.sentence_id,
            sentence_type=SentenceType.LAST,
            content_type=ContentType.ACTION,
        )
    )
    conn.dialogue.put(Message(role="assistant", content=text))


def _execute_tool_with_existing_pipeline(
    conn: "ConnectionHandler",
    function_call_data: Dict[str, Any],
):
    _wait_for_tool_ready(conn, function_call_data.get("name"))
    function_name = function_call_data["name"]
    tool_input = _load_arguments(function_call_data.get("arguments"))
    enqueue_tool_report(conn, function_name, tool_input)

    tool_call_timeout = int(conn.config.get("tool_call_timeout", 600))

    # 长任务先给用户一句语音反馈
    display = _display_tool_name(function_name)
    _speak_text(conn, f"好的，{display}开始执行，完成后告诉你结果。")

    try:
        result = asyncio.run_coroutine_threadsafe(
            conn.func_handler.handle_llm_function_call(conn, function_call_data),
            conn.loop,
        ).result(timeout=tool_call_timeout)
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"确认后工具调用失败: {e}")
        result = ActionResponse(
            action=Action.ERROR,
            result="工具调用超时，请一会再试下哈",
            response="工具调用超时，请一会再试下哈",
        )

    enqueue_tool_report(
        conn,
        function_name,
        tool_input,
        str(result.result) if result.result else None,
        report_tool_call=False,
    )
    conn._handle_function_result([(result, function_call_data)], depth=0)


def _wait_for_tool_ready(
    conn: "ConnectionHandler",
    function_name: str | None,
    timeout_seconds: float = 10.0,
) -> None:
    if not function_name or not getattr(conn, "func_handler", None):
        return

    deadline = time.monotonic() + timeout_seconds
    while time.monotonic() < deadline:
        handler = conn.func_handler
        if getattr(handler, "finish_init", False):
            tool_manager = getattr(handler, "tool_manager", None)
            if tool_manager and hasattr(tool_manager, "resolve_tool_name"):
                resolved = tool_manager.resolve_tool_name(function_name)
                if resolved != function_name:
                    function_name = resolved
            if handler.has_tool(function_name):
                return
        time.sleep(0.1)

    try:
        supported = conn.func_handler.current_support_functions()
    except Exception:
        supported = []
    conn.logger.bind(tag=TAG).warning(
        f"确认后工具仍未就绪: {function_name}, supported={supported}"
    )


async def accept_pending_proposal(conn: "ConnectionHandler") -> None:
    pending = conn.pending_proposal
    if not pending:
        conn.sentence_id = str(uuid.uuid4().hex)
        _speak_text(conn, "当前没有待确认的提案。")
        return

    function_call_data = pending["function_call_data"]
    conn.pending_proposal = None
    await send_proposal_message(
        conn,
        "accepted",
        {
            "function_name": _display_tool_name(function_call_data["name"]),
            "task": pending.get("task"),
        },
    )
    _prepare_tts_round(conn)

    def process_accept():
        try:
            _execute_tool_with_existing_pipeline(conn, function_call_data)
        finally:
            asyncio.run_coroutine_threadsafe(
                send_proposal_message(
                    conn,
                    "completed",
                    {
                        "function_name": _display_tool_name(function_call_data["name"]),
                        "task": pending.get("task"),
                    },
                ),
                conn.loop,
            ).result(timeout=5)
            _finish_tts_round(conn)

    conn.executor.submit(process_accept)


async def reject_pending_proposal(conn: "ConnectionHandler") -> None:
    pending = conn.pending_proposal
    conn.pending_proposal = None
    await send_proposal_message(
        conn,
        "rejected",
        {
            "function_name": _display_tool_name(pending.get("function_name")) if pending else None,
            "task": pending.get("task") if pending else None,
        },
    )
    conn.sentence_id = str(uuid.uuid4().hex)
    _speak_text(conn, "已取消。")


async def switch_pending_proposal_agent(
    conn: "ConnectionHandler", agent_id: str | None
) -> None:
    pending = conn.pending_proposal
    if not pending:
        conn.sentence_id = str(uuid.uuid4().hex)
        _speak_text(conn, "当前没有待确认的提案。")
        return

    if not agent_id:
        conn.sentence_id = str(uuid.uuid4().hex)
        _speak_text(conn, "没有收到新的 agent。")
        return

    arguments = _load_arguments(pending["function_call_data"].get("arguments"))
    arguments["agent_id"] = agent_id
    pending["agent_id"] = agent_id
    pending["function_call_data"]["arguments"] = _dump_arguments(arguments)
    pending["proposal_text"] = _build_proposal_text(
        pending["function_name"], arguments
    )

    await send_proposal_message(
        conn,
        "pending",
        {
            "function_name": _display_tool_name(pending["function_name"]),
            "proposal_text": pending["proposal_text"],
            "task": pending.get("task"),
        },
    )
    conn.sentence_id = str(uuid.uuid4().hex)
    _speak_text(conn, pending["proposal_text"])
