# CodePower AI — 语音版多 Agent 运营助手

把一个多 agent 运营系统(完整 OpenClaw Gateway + Hermes + Codex/Claude Code)接到语音界面。一句话说"派 planner 做 XXX",小智就用 GPT 理解意图、调 MCP、派给 agent 执行,用 EdgeTTS 语音播报结果。

**硬件目标**:装在充电宝里的随身 coding 助手(ESP32 + 麦克风)。黑客松期间用浏览器模拟麦克风演示。

```
麦克风/浏览器
   │  WebSocket(opus)
   ▼
xiaozhi-esp32-server(8000 / 8003)
   │  MCP streamable-http
   ▼
dispatcher(127.0.0.1:9001)       ← 本仓库核心代码
   │
   ├── OpenClaw Gateway(openclaw agent / openclaw mcp serve)
   ├── Hermes(独立后端)
   ├── 本机 Codex CLI / Claude Code CLI
   ├── xiaozhi chat 模式直连 JoyInside voiceChat
   ├── JoyInside skill gateway 入站回调(可选,127.0.0.1:9100)
   └── PowCoder visual dashboard(127.0.0.1:9200)
```

---

## 技术栈

| 层 | 选型 | 说明 |
|------|------|------|
| 运行环境 | Python 3.10 venv(uv 管理)| ARM64 原生,Docker Rosetta 太慢不用 |
| ASR | FunASR / SenseVoiceSmall(本地) | 中文识别,首次下载约 900MB |
| LLM | 任意 OpenAI 兼容 + function_call | 默认 gpt-5.4 via 86gamestore,可换 openrouter / 自建 vLLM |
| Intent | function_call | 复用主 LLM,不另起模型 |
| TTS | EdgeTTS | 免费,zh-CN-XiaoxiaoNeural 女声 |
| MCP | streamable-http(`mcp>=1.22`) | 官方 Python SDK |
| 默认任务后端 | OpenClaw Gateway | `openclaw agent --agent ... --json` |
| 独立后端 | [Hermes](https://github.com/nous-research/hermes) | `hermes chat -q ... -Q --yolo` |
| 本机 MCP | OpenClaw MCP stdio | `openclaw mcp serve --url ws://127.0.0.1:18789` |

---

## 快速开始(首次接入 0→1)

### 0. 前置环境

- macOS arm64(M 系列)或 Linux
- [uv](https://github.com/astral-sh/uv) — Python 版本和包管理
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- 一个 OpenAI 兼容 + 支持 function_call 的 LLM(gpt-4/gpt-5 系、Qwen、DeepSeek v3 都行)
- OpenClaw CLI / Gateway — 默认任务后端和本机 MCP 连接,详见下面
- (可选)Hermes CLI — 作为独立工程任务后端,详见下面
- (可选)OpenClaw Lite — 只作为 legacy dispatch.sh 后端保留,默认不使用

### 1. 克隆本仓库

```bash
git clone <THIS_REPO_URL> xiaozhi-hackathon
cd xiaozhi-hackathon
```

### 2. 一键安装(克隆小智源码 + 装两个 venv)

```bash
./scripts/setup.sh
```

这步会:
- 克隆 xinnan-tech/xiaozhi-esp32-server 到 `repo/`
- 装 `repo/main/xiaozhi-server/.venv/`(Python 3.10)
- 装 `dispatcher/.venv/`
- 把 `data/.config.yaml` 和 `.mcp_server_settings.json` 软链到 xiaozhi-server 的 data 目录
- 拷贝 `data/.config.yaml.example → data/.config.yaml`

### 3. 填环境变量

复制 `.env.example` 为本地 `.env`,填入实际密钥；`.env` 已被 `.gitignore` 忽略。

```bash
cp .env.example .env
```

`data/.config.yaml` 支持 `${ENV_NAME}` 占位符，例如 `CODEPOWER_LLM_API_KEY`、`OPENAI_ASR_API_KEY`、`DOUBAO_TTS_APPID`、`DOUBAO_TTS_ACCESS_TOKEN`。

**任何 OpenAI 兼容 + 支持 function_call 的接口都行**。比如:
- [86gamestore](https://86gamestore.com) — 中转站,gpt/claude 都便宜
- [openrouter](https://openrouter.ai) — 全球路由
- [DeepSeek 官方](https://platform.deepseek.com) — deepseek-chat 支持 function_call
- 自建 vLLM / ollama(需要模型本身支持 function_call)

### 4. 修补小智源码(修首轮 MCP 竞态)

打开 `repo/main/xiaozhi-server/core/connection.py`,找到 `chat()` 方法里 `functions = None` 那一段,替换为:

```python
functions = None
if (self.intent_type == "function_call" and hasattr(self, "func_handler") and not force_final_answer):
    # 等待 MCP 等异步初始化完成,避免首轮对话时 MCP 工具还没挂上
    _init_wait = 0
    while (self.func_handler is not None
           and not getattr(self.func_handler, "finish_init", False)
           and _init_wait < 50):
        time.sleep(0.1)
        _init_wait += 1
    functions = self.func_handler.get_functions()
```

只加 7 行,修的是"首次对话时 MCP 工具还没注册完"的竞态。

### 5. 启动

```bash
./scripts/start.sh
# 看日志: ./scripts/logs.sh
# 停止:   ./scripts/stop.sh
```

首次启动会自动下载 SenseVoiceSmall ASR 模型(约 900MB,5 分钟左右)。

### 6. 测试

```bash
cd dispatcher
source .venv/bin/activate

# ① dispatcher 自身(不经过小智)
python3 test_client.py list                                # 列出当前 MCP 工具
python3 test_client.py call list_agents                    # 应返回 agent 列表

# ② 端到端 WebSocket(模拟小智设备发文字)
python3 test_xiaozhi_ws.py "列出所有可用的 agent"
python3 test_xiaozhi_ws.py "读今天的日报"
python3 test_xiaozhi_ws.py "派 planner 用一句话总结今天最紧急的 3 件事"
python3 test_xiaozhi_ws.py "讲个很短的故事" chat
python3 test_xiaozhi_ws.py "让 OpenClaw 只回复 OK" task --accept

# ③ 真麦克风语音
python3 -m http.server 8006 --directory \
  repo/main/xiaozhi-server/test &
open http://localhost:8006/test_page.html
# 本机浏览器测试:
# 设置 → OTA 地址填: http://127.0.0.1:8003/xiaozhi/ota/
#
# 局域网硬件测试:
# 设置 → OTA 地址填: http://你的宿主机局域网IP:8003/xiaozhi/ota/
# data/.config.yaml 里的 server.websocket 保留“你的局域网IP”占位时,
# OTA 会自动替换为当前宿主机局域网 IP。
```

### 7. PowCoder 可视化状态页

可视化页用于演示和调试小智 / JoyInside / dispatcher / Agent 的联动状态。它不是独立聊天入口,而是读取 PowCoder 写入的状态文件和事件流,实时展示:

- 设备连接状态、当前 `chat/task/auto` 模式
- 语音对话输入与模型回复
- dispatcher proposal 待确认 / 已采纳 / 已拒绝状态
- OpenClaw、Hermes、Codex、Claude Code 等 worker 运行状态
- 最近 session 和任务链路

启动可视化服务:

```bash
./scripts/start_powcoder_visual.sh
open http://127.0.0.1:9200/
```

可视化服务会暴露这些本地接口:

```text
GET /api/state     # 当前聚合状态
GET /api/events    # 最近事件日志
GET /api/sessions  # 最近 session 列表
```

联动测试方式:

```bash
# 先启动主服务
./scripts/start.sh

# 再启动可视化页
./scripts/start_powcoder_visual.sh

# 浏览器测试页,底部可切换“闲聊 / GPT”
python3 -m http.server 8006 --directory repo/main/xiaozhi-server/test
open http://127.0.0.1:8006/test_page.html
```

在小智测试页发送消息后,`http://127.0.0.1:9200/` 会同步刷新终端日志、语音对话、Agent 卡片和工作链路。也可以用命令行直接打端到端链路:

```bash
cd dispatcher
source .venv/bin/activate
python3 test_xiaozhi_ws.py "讲个很短的故事" chat
python3 test_xiaozhi_ws.py "让 OpenClaw 只回复 OK" task --accept
```

演示截图:

![PowCoder 可视化状态页](docs/images/powcoder-visual-dashboard.png)

---

## JoyInside 接入

这里有两条链路,用途不同:

1. **模式分流**:task 模式继续用自己的 `Gpt54LLM` 做 function calling,负责 OpenClaw、Hermes、Codex、Claude Code、分身派发等任务;chat 模式在 xiaozhi-server 内直连 `JoyInsideLLM`,负责陪伴、游戏、讲故事、电子宠物等互动能力。
2. **JoyInside 云端回调 CodePower**:把本仓库的 `joyinside_gateway` 暴露成公网 HTTPS,让 JoyInside 平台里的自定义技能反过来调用 `list_agents`、`dispatch_agent`、`read_daily_report` 等本地工具。这条链路需要部署或 Cloudflare Tunnel。

### 配置环境变量

在 `.env` 里填 JoyInside 出站调用所需参数:

```bash
JOYINSIDE_ACCESS_KEY=
JOYINSIDE_SECRET_KEY=
JOYINSIDE_VENDOR_ID=
JOYINSIDE_APP_ID=
JOYINSIDE_DEVICE_ID=codepower-local-xiaozhi
JOYINSIDE_DEVICE_NAME=CodePower-Local-Xiaozhi
JOYINSIDE_BOT_ID=          # 可选;留空时会按 vendor/app/device 注册拿 botId
JOYINSIDE_UID=codepower-local-user
```

保持 `data/.config.yaml`:

```yaml
selected_module:
  LLM: Gpt54LLM
  Intent: function_call
```

这时 task 模式主 LLM 还是自己的 OpenAI 兼容模型。需要 JoyInside 的讲故事、游戏、电子宠物等能力时,用 chat 模式发送消息。

### 验证 JoyInside 出站能力

验证小智端到端链路:

```bash
cd dispatcher
source .venv/bin/activate
python3 test_xiaozhi_ws.py "讲个很短的故事" chat
```

调通的信号:

- 终端能收到 JoyInside 返回的故事、游戏、电子宠物等互动内容。
- 小智日志里能看到 `闲聊模式 → JoyInside`。
- task 模式日志仍显示自己的 LLM,例如 `llm成功 Gpt54LLM`,说明任务链路没有切给 JoyInside。

### 切成 JoyInside 当主 LLM

如果要整套小智对话都走 JoyInside,把 `data/.config.yaml` 改成:

```yaml
selected_module:
  LLM: JoyInsideLLM
```

这个模式会绕过本地 `Gpt54LLM` 的人设和工具路由,主回答来自 JoyInside 智能体。若 JoyInside 平台配置的人设没有生效,优先核对平台侧 app/bot/device 绑定、配置是否发布、`JOYINSIDE_APP_ID` 和 `JOYINSIDE_BOT_ID` 是否指向同一个已配置应用;本地 prompt 不会覆盖 JoyInside 平台的人设。

### 暴露 CodePower 给 JoyInside 自定义技能

`http://127.0.0.1:9100/joyinside/skill?tool=list_agents` 是给 JoyInside 平台调用的入站 HTTP/SSE 接口。本机 curl 能通,只代表 gateway 本地正常;JoyInside 云端要调用它,必须有公网 HTTPS。

本地启动:

```bash
JOYINSIDE_SERVICE_TOKEN=dev-token ./scripts/start_joyinside_gateway.sh
```

本地测试:

```bash
curl -N -X POST 'http://127.0.0.1:9100/joyinside/skill?tool=list_agents' \
  -H 'Authorization: Bearer dev-token' \
  -H 'Content-Type: application/json' \
  -d '{"parameters":{"input":"列出所有可用 agent","session_id":"local","bot_id":"local"}}'
```

平台配置时,用 Cloudflare Tunnel 或正式部署把本地 9100 暴露成公网 HTTPS:

```bash
cloudflared tunnel --url http://127.0.0.1:9100
```

然后在 JoyInside 自定义技能里配置:

- API URL: `https://<your-public-domain>/joyinside/skill?tool=list_agents`
- Auth: Service Token
- Token header: `Authorization: Bearer <JOYINSIDE_SERVICE_TOKEN>`
- Response mode: streaming SSE,事件为 `Message` 和 `Done`

可注册多个技能,只改 query 参数:

- `tool=list_agents`
- `tool=read_daily_report`
- `tool=query_agent_status`
- `tool=dispatch_agent`

---

## 接入完整 OpenClaw Gateway(默认任务后端)

本仓库现在默认走完整 OpenClaw,不是 OpenClaw Lite。需要本机有 `openclaw` CLI,并启动 Gateway:

```bash
openclaw gateway status
# 如果没运行:
openclaw gateway start
```

默认配置:

```bash
CODEPOWER_AGENT_BACKEND=openclaw
CODEPOWER_AGENT_BACKENDS=openclaw,hermes
CODEPOWER_OPENCLAW_DEFAULT_AGENT=planner
CODEPOWER_OPENCLAW_AGENTS=planner:规划师,site-ops:站点运维,support:客服,overseas-dev:出海开发,designer:设计师,keyword-miner:挖词官
CODEPOWER_OPENCLAW_GATEWAY_URL=ws://127.0.0.1:18789
```

`CODEPOWER_OPENCLAW_AGENTS` 是可选的本地 agent 清单。配置后服务启动不会依赖 `openclaw agents list --json` 的探测结果;不配置时 dispatcher 会自动探测 Gateway agent。

小智会同时加载两个 MCP server:

```json
{
  "mcpServers": {
    "openclaw-dispatcher": {
      "url": "http://127.0.0.1:9001/mcp",
      "transport": "streamable-http"
    },
    "openclaw-local": {
      "command": "openclaw",
      "args": ["mcp", "serve", "--url", "ws://127.0.0.1:18789", "--claude-channel-mode", "off"]
    }
  }
}
```

验证:

```bash
openclaw agents list --json
openclaw agent --agent planner --message "只回复 OK，用于连通性自测。" --json --timeout 60
cd dispatcher
source .venv/bin/activate
python3 test_client.py call list_agent_backends
python3 test_client.py call openclaw_agent_task planner "只回复 OK"
```

`dispatch_agent(agent_id, task)` 默认等价于走 OpenClaw。需要显式走 Hermes 时传 `backend=hermes`,或直接用 `hermes_repo_task(task)`。

---

## 接入 Hermes(可选,独立后端)

Hermes 是本地运行的 agent CLI,走 OpenAI 兼容中转便宜。

### 装 Hermes

按 [nous-research/hermes](https://github.com/nous-research/hermes) 官方文档装,得到 `hermes` 可执行文件(默认 `~/.local/bin/hermes`)。

### 配 Hermes 的 LLM

编辑 `~/.hermes/config.yaml`:

```yaml
model:
  default: gpt-5.4                            # 你用的模型
  provider: custom
  base_url: https://api.86gamestore.com/v1    # 同中转 API
  api_key: "YOUR_API_KEY"

custom_providers:
- name: relay
  base_url: https://api.86gamestore.com/v1
  api_key: YOUR_API_KEY
  model: gpt-5.4
```

### 验证

```bash
hermes chat -q "你好,一句话自我介绍" -Q --yolo --source tool
# 应在 10~20 秒内返回一句话
```

dispatcher 会自动识别 `~/.local/bin/hermes`。Hermes 不再和 OpenClaw 混在一起:显式调用 `hermes_repo_task(task)`,或配置 `CODEPOWER_AGENT_BACKEND=hermes` 后让 `dispatch_agent` 走 Hermes。

---

## 接入 OpenClaw Lite(可选 legacy 后端)

OpenClaw Lite 是旧的 `dispatch.sh + claude -p` 调度路径。本仓库保留 `openclaw_lite` 后端,但默认不再使用。

### 装 OpenClaw Lite

```bash
# 克隆并装到 ~/.openclaw/lite/
# (具体安装步骤参见 openclaw-lite 项目)
```

装好后应该能看到:
- `~/.openclaw/lite/agents.json` — agent 注册表
- `~/.openclaw/lite/bin/dispatch.sh` — 派发脚本
- `~/.openclaw/workspace/logs/daily/YYYY-MM-DD.md` — 日报

### 最简 agents.json 示例

如果你不装完整 OpenClaw,可以手写一份最小 `~/.openclaw/lite/agents.json` 让 `list_agents` 有返回:

```json
{
  "agents": {
    "main":          {"role": "主协调/默认执行", "emoji": "🎯"},
    "planner":       {"role": "规划师/日报周报",  "emoji": "📋"},
    "site-ops":      {"role": "运维监控",        "emoji": "🛡️"},
    "support":       {"role": "客服邮件",        "emoji": "📬"},
    "overseas-dev":  {"role": "出海开发/外链/SEO","emoji": "🌏"},
    "designer":      {"role": "设计/品牌视觉",   "emoji": "🎨"},
    "keyword-miner": {"role": "关键词挖掘",      "emoji": "⛏️"}
  }
}
```

如需显式启用 Lite:

```bash
CODEPOWER_AGENT_BACKENDS=openclaw,hermes,openclaw_lite
CODEPOWER_AGENT_FALLBACK_BACKENDS=openclaw_lite
```

没有日报文件时 `read_daily_report` 会返回空目录提示。

---

## MCP 工具(dispatcher 暴露)

`http://127.0.0.1:9001/mcp` 暴露这些工具:

| 工具 | 用途 | 调用路径 |
|------|------|---------|
| `list_agents()` | 列出 agent | 优先读完整 OpenClaw Gateway,失败才读 Lite agents.json |
| `list_agent_backends()` | 查看后端配置 | 读 `CODEPOWER_AGENT_BACKEND(S)` 等环境变量 |
| `dispatch_agent(agent_id, task, backend)` | 派发任务 | 默认 OpenClaw Gateway;可选 Hermes / OpenClaw Lite |
| `openclaw_agent_task(agent_id, task)` | 显式调用完整 OpenClaw | `openclaw agent --agent ... --json` |
| `query_agent_status()` | 查最近一次任务 | 读 `/tmp/xiaozhi-dispatcher-state.json` |
| `read_daily_report(date)` | 读日报 | 读 `~/.openclaw/workspace/logs/daily/*.md` |
| `hermes_repo_task(task)` | 让 Hermes 执行通用工程任务 | 默认 `~/Desktop/work_space/hemers_work_dir`，可用 `CODEPOWER_HERMES_WORKSPACE` 改 |
| `run_codex(task, workdir, allow_edits)` | 调本机 Codex CLI | 默认只读，明确修改时才允许编辑 |
| `run_claude_code(task, workdir, allow_edits)` | 调本机 Claude Code CLI | 默认只读，明确修改时才允许编辑 |

想加新工具?在 `dispatcher/server.py` 加一个 `@mcp.tool()` 即可,小智会自动拿到。

---

## 目录结构

```
xiaozhi-hackathon/
├── README.md                     # 本文件
├── PLAN.md                       # 黑客松设计文档
├── docker-compose.yml            # (备选)Docker 部署,Mac arm64 不推荐
├── data/
│   ├── .config.yaml.example      # 小智配置模板(进仓库)
│   ├── .config.yaml              # 实际配置(含 api_key, .gitignore)
│   └── .mcp_server_settings.json # MCP 接入点:dispatcher + openclaw-local
├── models/SenseVoiceSmall/       # ASR 模型(模型文件 .gitignore)
├── dispatcher/                   # 自研 MCP server
│   ├── server.py                 # MCP 工具服务
│   ├── test_client.py            # MCP client 测试
│   ├── test_xiaozhi_ws.py        # WebSocket 端到端测试
│   └── requirements.txt
├── repo/                         # (.gitignore)克隆的小智源码
│   └── main/xiaozhi-server/
├── scripts/
│   ├── setup.sh                  # 一键安装
│   ├── start.sh                  # 一键启动
│   ├── stop.sh                   # 停
│   └── logs.sh                   # 跟日志
└── demo/
    └── demo-script.md            # 黑客松演示脚本
```

---

## 关键配置点(避坑)

1. **LLM 必须支持 function calling** — 不支持的话工具不会被调。已验证 gpt-5.4(86gamestore)、deepseek-chat、openai gpt-4o 都支持。
2. **`tool_call_timeout: 300`** — `.config.yaml` 里默认 300s。默认 30s 对 OpenClaw / Hermes / Codex / Claude Code 不够。
3. **SOCKS 代理会干扰 httpx** — `start.sh` 已 unset 所有代理变量。如果你自己起 dispatcher,记得先 `unset ALL_PROXY HTTPS_PROXY HTTP_PROXY`。
4. **首轮 MCP 竞态** — 改了 `core/connection.py` 7 行,见上面「修补小智源码」。
5. **prompt 里必须列出工具名** — LLM 拿到 `tools=[...]` 但偶尔会幻觉"没这功能",所以在 system prompt 里明确罗列工具 + 路由规则,成功率接近 100%。
6. **硬件局域网测试不需要公网隧道** — 同一 Wi-Fi 下优先用 `http://宿主机IP:8003/xiaozhi/ota/`。不要随手启动 `cloudflared tunnel --url ...`，它会把本机服务发布到公网入口。
7. **JoyInside 本地能力和公网技能不是一回事** — chat 模式是本地出站调 JoyInside;`joyinside_gateway` 是 JoyInside 云端入站调本地 CodePower。只有后者需要公网 HTTPS。

---

## TTS 播报优化(语音场景的核心)

普通 prompt 让 LLM 输出文本,TTS 念出来一堆 ASCII(把 "planner" 念成 "P-L-A-N-N-E-R")或数字(把 "75%" 念成 "七十五 percent")。本仓库在 `data/.config.yaml.example` 的 prompt 里写了一套**语音播报铁律**:

- 英文 agent id 强制翻译(planner→规划师,site-ops→运维)
- 技术术语读法(GitHub→及特哈布,PR→合并请求,API→接口)
- 数字读约数("将近一千"不说 "946")
- 全角标点,60 字内,口语化

这是把"LLM 会写"变成"TTS 听着顺"的关键。改动主要集中在 prompt,没改 xiaozhi-server 源码。

---

## 常见问题

**Q: 可以不要 OpenClaw 吗?**
A: 可以。把 `CODEPOWER_AGENT_BACKEND=hermes`,并保留最简 `agents.json` 给 `list_agents` 和 agent_id 校验。

**Q: 可以不要 Hermes 吗?**
A: 可以。默认就是 OpenClaw Gateway。Hermes 只是独立可选后端。

**Q: 都不装呢?**
A: 那 `list_agents` 空,`dispatch_agent` 无路径可走。你可以只保留 `read_daily_report` + 自己加新 MCP 工具。

**Q: Windows 能跑吗?**
A: 没测。理论上 xiaozhi-server 官方支持 Windows,本仓库的 bash 脚本需要改成 pwsh。

**Q: 必须用中文 prompt 吗?**
A: 不必。改 `data/.config.yaml` 里的 `prompt:` 块成英文,TTS 换 `en-US-AriaNeural` 之类即可。

---

## License

MIT(本仓库)。依赖项目各有各的 license:
- xiaozhi-esp32-server — MIT
- Hermes — 按各自 license
- OpenClaw / OpenClaw Lite — 按各自 license
