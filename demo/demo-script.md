# 黑客松演示脚本 — 小智语音 × OpenClaw/Hermes 多 agent 运营

**时长:** 3–5 分钟
**设备:** 一台 Mac(或浏览器),无需 ESP32

---

## 演示结构

### 开场(30s)
> "这是一个把多 agent 运营系统接到语音的项目。平时我在终端里用 OpenClaw 调 planner、site-ops、designer 这些 agent,现在我可以直接用嘴说。整条链路是本地跑的:小智 ESP32 server 负责语音,后面接我自研的 MCP dispatcher,再派到 Hermes(gpt-5.4)或 Claude。"

展示架构图(PLAN.md 里那张)。

### 演示 1 — "列出所有 agent"(30s)
> 小智,列出所有可用的 agent

预期:小智声音播报 "现在有 7 个 agent,main 主协调,planner 规划,site-ops 运维,support 客服,overseas-dev 出海,designer 设计,keyword-miner 挖词"。

解说:
> "这条 MCP 工具叫 `list_agents`,它直接读我本地的 OpenClaw agent 注册表(`~/.openclaw/lite/agents.json`),一条命令 2 秒返回。"

### 演示 2 — "读今天日报"(40s)
> 小智,读一下今天的日报

预期:播报今日外链任务、Reddit 养号、邮件概况等。

解说:
> "日报是 OpenClaw scheduler 每天 21 点跑 `planner` 生成的 markdown,小智直接读文件,不走 LLM 再请求一次,省钱又快。"

### 演示 3 — "派 planner 做任务"(90s)
> 小智,派 planner 用一句话总结今天最紧急的 3 件事

等待约 20–45 秒,小智用口语念出 3 件事。

解说(等待期间可以说):
> "这一步走的是 Hermes 后端,Hermes 是本地的另一个 agent,用的是我 OpenAI 帐号以外的中转 API,模型是 gpt-5.4。Hermes 失败会自动回落到 Claude。这样既省钱又有兜底。"

### 演示 4 — "查刚才那个任务"(20s)
> 小智,刚才那个任务做完了吗

预期:播报 planner 已完成、后端、结果摘要。

解说:
> "所有派发的运行记录都存在 `/tmp/xiaozhi-dispatcher-runs/` 和 state file。问状态是直接读文件,不再跑 LLM。"

### 收尾(30s)
讲亮点:
- **全本地部署**,麦克风→小智→MCP→OpenClaw/Hermes 全部在 Mac 上跑
- **协议开放**,基于 MCP,接新工具只加一个 `@mcp.tool()`,可无限扩展
- **双后端路由**,Hermes 省钱、Claude 质量兜底,LLM 自动选
- **从 GUI/终端进化到对话界面**,从"打字 + 回车"变成"说一句 + 听一句"

---

## 现场准备清单

演示前 5 分钟:
```bash
cd ~/xiaozhi-hackathon

# 1. 启服务(dispatcher + xiaozhi-server)
./scripts/start.sh

# 2. 确认内部测试通过
cd dispatcher
source .venv/bin/activate
python3 test_xiaozhi_ws.py "列出可用 agent"   # 应该看到 agent 列表
python3 test_xiaozhi_ws.py "读今天日报"       # 应该看到日报开头

# 3. 打开浏览器测试页(用真人麦克风演示)
python3 -m http.server 8006 --directory \
  ~/xiaozhi-hackathon/repo/main/xiaozhi-server/test &
open http://localhost:8006/test_page.html
# 点右上"设置",WebSocket URL 填: ws://127.0.0.1:8000/xiaozhi/v1/
# 按住"按住说话"就可以开口
```

演示后:
```bash
./scripts/stop.sh
```

## 出问题的兜底

| 现象 | 回应 | 后备 |
|------|------|------|
| Hermes 超时 | "正常,它刚才在调 gpt-5.4 要 20 秒" | 继续等,最多 90s |
| 网络拉胯 | 切换到 **本地 Ollama**(需提前配) | 改用回放的预录音频 |
| 麦克风失败 | 用 `test_xiaozhi_ws.py` 发文本指令 | 演示还是走全链路 |
| LLM 没调工具 | 再说一次,措辞更明确("派 planner ...") | 改走"列 agent"这条最稳 |

## 测试命令速记

```bash
# 3 条 MVP 指令内部测试
python3 dispatcher/test_xiaozhi_ws.py "列出所有可用的 agent"
python3 dispatcher/test_xiaozhi_ws.py "读一下今天的日报"
python3 dispatcher/test_xiaozhi_ws.py "派 planner 用一句话总结今天最紧急的 3 件事"
python3 dispatcher/test_xiaozhi_ws.py "刚才那个任务做完了吗"

# 直测 dispatcher (不走语音)
python3 dispatcher/test_client.py call list_agents
python3 dispatcher/test_client.py call dispatch_agent planner "查今天任务"
```
