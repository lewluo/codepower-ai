"""Quick MCP client to verify dispatcher works locally."""
import asyncio
import os
import sys

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client


def _local_http_client(headers=None, timeout=None, auth=None):
    return httpx.AsyncClient(
        headers=headers,
        timeout=timeout,
        auth=auth,
        trust_env=False,
    )


async def main(url: str, action: str, *args: str):
    async with streamablehttp_client(
        url,
        httpx_client_factory=_local_http_client,
    ) as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            if action == "list":
                tools = await session.list_tools()
                for t in tools.tools:
                    print(f"- {t.name}: {t.description}")
                return
            if action == "call":
                tool_name = args[0]
                payload = {}
                if tool_name == "dispatch_agent" and len(args) >= 3:
                    payload = {"agent_id": args[1], "task": args[2]}
                elif tool_name == "read_daily_report" and len(args) >= 2:
                    payload = {"date": args[1]}
                elif tool_name in {"run_codex", "run_claude_code"} and len(args) >= 2:
                    payload = {"task": args[1]}
                    if len(args) >= 3:
                        payload["workdir"] = args[2]
                elif tool_name == "hermes_repo_task" and len(args) >= 2:
                    payload = {"task": args[1]}
                result = await session.call_tool(tool_name, payload)
                for content in result.content:
                    print(getattr(content, "text", content))
                return


if __name__ == "__main__":
    url = os.environ.get("MCP_URL", "http://127.0.0.1:9001/mcp")
    action = sys.argv[1] if len(sys.argv) > 1 else "list"
    asyncio.run(main(url, action, *sys.argv[2:]))
