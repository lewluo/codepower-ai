import json
import uuid
import asyncio
import re
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from core.connection import ConnectionHandler
from core.utils.dialogue import Message
from core.providers.tts.dto.dto import ContentType
from core.handle.helloHandle import checkWakeupWords
from plugins_func.register import Action, ActionResponse
from core.handle.sendAudioHandle import send_stt_message
from core.handle.reportHandle import enqueue_tool_report
from core.handle.proposalHandler import stage_pending_proposal
from core.utils.util import remove_punctuation_and_length
from core.providers.tts.dto.dto import TTSMessageDTO, SentenceType

TAG = __name__
DIRECT_HERMES_ALIAS_RE = re.compile(r"(hermes|hummus|赫尔墨斯|赫耳墨斯)", re.IGNORECASE)
DIRECT_HERMES_REQUEST_RE = re.compile(
    r"(用|让|叫|请让|请叫|交给|麻烦|帮我让|帮我叫|帮我用|由).{0,8}(hermes|hummus|赫尔墨斯|赫耳墨斯)",
    re.IGNORECASE,
)
DIRECT_OPENCLAW_ALIAS_RE = re.compile(r"(open\s*claw|openclaw|欧喷克劳)", re.IGNORECASE)
DIRECT_OPENCLAW_REQUEST_RE = re.compile(
    r"(用|让|叫|请让|请叫|交给|麻烦|帮我让|帮我叫|帮我用|由).{0,8}(open\s*claw|openclaw|欧喷克劳)",
    re.IGNORECASE,
)
OPENCLAW_AGENT_ALIASES = {
    "planner": ["planner", "规划师", "计划", "规划"],
    "site-ops": ["site-ops", "site ops", "运维", "站点"],
    "support": ["support", "客服", "邮件"],
    "overseas-dev": ["overseas-dev", "overseas dev", "出海", "海外"],
    "designer": ["designer", "设计师", "设计"],
    "keyword-miner": ["keyword-miner", "keyword miner", "挖词官", "挖词", "关键词"],
}


async def handle_user_intent(conn: "ConnectionHandler", text):
    # 预处理输入文本，处理可能的JSON格式
    try:
        if text.strip().startswith("{") and text.strip().endswith("}"):
            parsed_data = json.loads(text)
            if isinstance(parsed_data, dict) and "content" in parsed_data:
                text = parsed_data["content"]  # 提取content用于意图分析
                conn.current_speaker = parsed_data.get("speaker")  # 保留说话人信息
    except (json.JSONDecodeError, TypeError):
        pass

    # 检查是否有明确的退出命令
    _, filtered_text = remove_punctuation_and_length(text)
    if await check_direct_exit(conn, filtered_text):
        return True

    # 明确再见不被打断
    if conn.is_exiting:
        return True

    # 检查是否是唤醒词
    if await checkWakeupWords(conn, filtered_text):
        return True

    # 闲聊模式下跳过工具相关的意图识别，直接进入 chat() 走 JoyInside
    if conn.client_listen_mode == "chat":
        return False

    if await try_handle_direct_openclaw_request(conn, text):
        return True

    if await try_handle_direct_hermes_request(conn, text):
        return True

    if conn.intent_type == "function_call":
        # 使用支持function calling的聊天方法,不再进行意图分析
        return False
    # 使用LLM进行意图分析
    intent_result = await analyze_intent_with_llm(conn, text)
    if not intent_result:
        return False
    # 会话开始时生成sentence_id
    conn.sentence_id = str(uuid.uuid4().hex)
    # 处理各种意图
    return await process_intent_result(conn, intent_result, text)


async def check_direct_exit(conn: "ConnectionHandler", text):
    """检查是否有明确的退出命令"""
    _, text = remove_punctuation_and_length(text)
    cmd_exit = conn.cmd_exit
    for cmd in cmd_exit:
        if text == cmd:
            conn.logger.bind(tag=TAG).info(f"识别到明确的退出命令: {text}")
            await send_stt_message(conn, text)
            conn.is_exiting = True
            await conn.close()
            return True
    return False


async def analyze_intent_with_llm(conn: "ConnectionHandler", text):
    """使用LLM分析用户意图"""
    if not hasattr(conn, "intent") or not conn.intent:
        conn.logger.bind(tag=TAG).warning("意图识别服务未初始化")
        return None

    # 对话历史记录
    dialogue = conn.dialogue
    try:
        intent_result = await conn.intent.detect_intent(conn, dialogue.dialogue, text)
        return intent_result
    except Exception as e:
        conn.logger.bind(tag=TAG).error(f"意图识别失败: {str(e)}")

    return None


def _normalize_direct_hermes_task(text: str) -> str:
    task = text.strip()
    task = re.sub(
        r"^(请)?(你)?(帮我)?(让|叫|请让|请叫|交给|麻烦|由)\s*(hermes|hummus|赫尔墨斯|赫耳墨斯)\s*(去|来|直接)?",
        "",
        task,
        flags=re.IGNORECASE,
    ).strip()
    task = re.sub(
        r"^(帮我|替我|直接)\s*",
        "",
        task,
        flags=re.IGNORECASE,
    ).strip()
    return task or text.strip()


def _normalize_direct_openclaw_task(text: str) -> str:
    task = text.strip()
    task = re.sub(
        r"^(请)?(你)?(帮我)?(让|叫|请让|请叫|交给|麻烦|由)\s*(open\s*claw|openclaw|欧喷克劳)\s*(去|来|直接)?",
        "",
        task,
        flags=re.IGNORECASE,
    ).strip()
    task = re.sub(
        r"^(帮我|替我|直接)\s*",
        "",
        task,
        flags=re.IGNORECASE,
    ).strip()
    return task or text.strip()


def _infer_openclaw_agent_id(text: str) -> str:
    lowered = text.lower()
    for agent_id, aliases in OPENCLAW_AGENT_ALIASES.items():
        if any(alias in lowered or alias in text for alias in aliases):
            return agent_id
    return "planner"


async def try_handle_direct_openclaw_request(
    conn: "ConnectionHandler", original_text: str
) -> bool:
    text = original_text.strip()
    if not text:
        return False

    if not DIRECT_OPENCLAW_ALIAS_RE.search(text):
        return False

    if not DIRECT_OPENCLAW_REQUEST_RE.search(text):
        return False

    task = _normalize_direct_openclaw_task(text)
    function_call_data = {
        "name": "openclaw_agent_task",
        "id": str(uuid.uuid4().hex),
        "arguments": json.dumps(
            {"agent_id": _infer_openclaw_agent_id(text), "task": task},
            ensure_ascii=False,
        ),
    }

    conn.logger.bind(tag=TAG).info(f"命中显式 OpenClaw 请求，直接进入确认链: {task}")
    await send_stt_message(conn, original_text)
    conn.client_abort = False
    return await stage_pending_proposal(conn, function_call_data, original_text)


async def try_handle_direct_hermes_request(
    conn: "ConnectionHandler", original_text: str
) -> bool:
    text = original_text.strip()
    if not text:
        return False

    if not DIRECT_HERMES_ALIAS_RE.search(text):
        return False

    if not DIRECT_HERMES_REQUEST_RE.search(text):
        return False

    task = _normalize_direct_hermes_task(text)
    function_call_data = {
        "name": "hermes_repo_task",
        "id": str(uuid.uuid4().hex),
        "arguments": json.dumps({"task": task}, ensure_ascii=False),
    }

    conn.logger.bind(tag=TAG).info(f"命中显式 Hermes 请求，直接进入确认链: {task}")
    await send_stt_message(conn, original_text)
    conn.client_abort = False
    return await stage_pending_proposal(conn, function_call_data, original_text)


async def process_intent_result(
    conn: "ConnectionHandler", intent_result, original_text
):
    """处理意图识别结果"""
    try:
        # 尝试将结果解析为JSON
        intent_data = json.loads(intent_result)

        # 检查是否有function_call
        if "function_call" in intent_data:
            # 直接从意图识别获取了function_call
            conn.logger.bind(tag=TAG).debug(
                f"检测到function_call格式的意图结果: {intent_data['function_call']['name']}"
            )
            function_name = intent_data["function_call"]["name"]
            if function_name == "continue_chat":
                return False

            if function_name == "result_for_context":
                await send_stt_message(conn, original_text)
                conn.client_abort = False

                def process_context_result():
                    conn.dialogue.put(Message(role="user", content=original_text))

                    from core.utils.current_time import get_current_time_info

                    current_time, today_date, today_weekday, lunar_date = (
                        get_current_time_info()
                    )

                    # 构建带上下文的基础提示
                    context_prompt = f"""当前时间：{current_time}
                                        今天日期：{today_date} ({today_weekday})
                                        今天农历：{lunar_date}

                                        请根据以上信息回答用户的问题：{original_text}"""

                    response = conn.intent.replyResult(context_prompt, original_text)
                    speak_txt(conn, response)

                conn.executor.submit(process_context_result)
                return True

            function_args = {}
            if "arguments" in intent_data["function_call"]:
                function_args = intent_data["function_call"]["arguments"]
                if function_args is None:
                    function_args = {}
            # 确保参数是字符串格式的JSON
            if isinstance(function_args, dict):
                function_args = json.dumps(function_args)

            function_call_data = {
                "name": function_name,
                "id": str(uuid.uuid4().hex),
                "arguments": function_args,
            }

            await send_stt_message(conn, original_text)
            conn.client_abort = False

            if await stage_pending_proposal(conn, function_call_data, original_text):
                return True

            # 准备工具调用参数
            tool_input = {}
            if function_args:
                if isinstance(function_args, str):
                    tool_input = json.loads(function_args) if function_args else {}
                elif isinstance(function_args, dict):
                    tool_input = function_args

            # 上报工具调用
            enqueue_tool_report(conn, function_name, tool_input)

            # 使用executor执行函数调用和结果处理
            def process_function_call():
                conn.dialogue.put(Message(role="user", content=original_text))
                
                # 工具调用超时时间
                tool_call_timeout = int(conn.config.get("tool_call_timeout", 30))
                # 使用统一工具处理器处理所有工具调用
                try:
                    result = asyncio.run_coroutine_threadsafe(
                        conn.func_handler.handle_llm_function_call(
                            conn, function_call_data
                        ),
                        conn.loop,
                    ).result(timeout=tool_call_timeout)
                except Exception as e:
                    conn.logger.bind(tag=TAG).error(f"工具调用失败: {e}")
                    result = ActionResponse(
                        action=Action.ERROR, result="工具调用超时，请一会再试下哈", response="工具调用超时，请一会再试下哈"
                    )

                # 上报工具调用结果
                if result:
                    enqueue_tool_report(conn, function_name, tool_input, str(result.result) if result.result else None, report_tool_call=False)

                    if result.action == Action.RESPONSE:  # 直接回复前端
                        text = result.response
                        if text is not None:
                            speak_txt(conn, text)
                    elif result.action == Action.REQLLM:  # 调用函数后再请求llm生成回复
                        text = result.result
                        conn.dialogue.put(Message(role="tool", content=text))
                        llm_result = conn.intent.replyResult(text, original_text)
                        if llm_result is None:
                            llm_result = text
                        speak_txt(conn, llm_result)
                    elif (
                        result.action == Action.NOTFOUND
                        or result.action == Action.ERROR
                    ):
                        text = result.response if result.response else result.result
                        if text is not None:
                            speak_txt(conn, text)
                    elif function_name != "play_music":
                        # For backward compatibility with original code
                        # 获取当前最新的文本索引
                        text = result.response
                        if text is None:
                            text = result.result
                        if text is not None:
                            speak_txt(conn, text)

            # 将函数执行放在线程池中
            conn.executor.submit(process_function_call)
            return True
        return False
    except json.JSONDecodeError as e:
        conn.logger.bind(tag=TAG).error(f"处理意图结果时出错: {e}")
        return False


def speak_txt(conn: "ConnectionHandler", text):
    # 记录文本到 sentence_id 映射
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
