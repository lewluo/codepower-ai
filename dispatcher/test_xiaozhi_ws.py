"""
内部测试:直接以 WebSocket 客户端身份连 xiaozhi-server,
发送文字 "listen/detect",观察 LLM/TTS 事件流,验证 LLM + MCP 工具链路是否打通。

用法:
  python3 test_xiaozhi_ws.py "列出所有 agent"
  python3 test_xiaozhi_ws.py "让 planner 看看今天有什么任务"
  python3 test_xiaozhi_ws.py "读今天的日报"
"""
from __future__ import annotations

import asyncio
import json
import sys
import uuid

import websockets

WS_URL = "ws://127.0.0.1:8000/xiaozhi/v1/"


async def send_text(query: str, total_timeout: float = 90.0) -> None:
    device_id = f"aa:bb:cc:{uuid.uuid4().hex[:6]}"
    headers = {
        "device-id": device_id,
        "client-id": device_id,
        "protocol-version": "1",
    }
    print(f"[client] connecting as {device_id} ...")
    try:
        ws = await websockets.connect(WS_URL, additional_headers=headers, max_size=4 * 1024 * 1024)
    except TypeError:
        ws = await websockets.connect(WS_URL, extra_headers=headers, max_size=4 * 1024 * 1024)

    async with ws:
        hello = {
            "type": "hello",
            "version": 1,
            "features": {"mcp": False},
            "audio_params": {"format": "opus", "sample_rate": 16000, "channels": 1, "frame_duration": 60},
        }
        await ws.send(json.dumps(hello))
        print(f"[→] hello")

        welcome = await asyncio.wait_for(ws.recv(), timeout=10)
        print(f"[←] welcome: {welcome[:200]}")

        detect = {"type": "listen", "state": "detect", "text": query}
        await ws.send(json.dumps(detect))
        print(f"[→] listen/detect: {query}")

        llm_pieces: list[str] = []
        end = asyncio.get_event_loop().time() + total_timeout
        saw_stop = False
        while asyncio.get_event_loop().time() < end:
            try:
                msg = await asyncio.wait_for(ws.recv(), timeout=5)
            except asyncio.TimeoutError:
                if saw_stop:
                    break
                continue
            if isinstance(msg, bytes):
                # 跳过 TTS opus 帧
                continue
            try:
                obj = json.loads(msg)
            except Exception:
                print(f"[←] raw: {msg[:120]}")
                continue
            mtype = obj.get("type")
            if mtype == "stt":
                print(f"[← stt] {obj.get('text')}")
            elif mtype == "llm":
                piece = obj.get("text") or ""
                if piece:
                    llm_pieces.append(piece)
                    print(f"[← llm] {piece}")
            elif mtype == "tts":
                state = obj.get("state")
                text = obj.get("text")
                if text:
                    print(f"[← tts/{state}] {text}")
                elif state == "stop":
                    saw_stop = True
                    print(f"[← tts/stop]")
                    # stop 之后稍微再等一下看还有没有
                    try:
                        msg2 = await asyncio.wait_for(ws.recv(), timeout=2)
                        if isinstance(msg2, str):
                            print(f"[←] post-stop: {msg2[:200]}")
                    except asyncio.TimeoutError:
                        pass
                    break
            else:
                print(f"[← {mtype}] {json.dumps(obj, ensure_ascii=False)[:200]}")

        print("---")
        print(f"[final llm] {''.join(llm_pieces)}")


if __name__ == "__main__":
    query = sys.argv[1] if len(sys.argv) > 1 else "你好,你是谁?"
    asyncio.run(send_text(query))
