# CodePower AI — 语音版多 Agent 运营助手

把一个多 agent 运营系统(OpenClaw Lite + Hermes)接到语音界面。一句话说"派 planner 做 XXX",小智就用 gpt 理解意图、调 MCP、派给 agent 执行,用 EdgeTTS 语音播报结果。

**硬件目标**:装在充电宝里的随身 coding 助手(ESP32 + 麦克风)。黑客松期间用浏览器模拟麦克风演示。

```
麦克风/浏览器
   │  WebSocket(opus)
   ▼
xiaozhi-esp32-server(8000 / 8003)
   │  MCP streamable-http
   ▼
dispatcher(127.0.0.1:9000)       ← 本仓库核心代码
   │
   ├── Hermes(主路,gpt-5.4 中转) ← 快,便宜
   └── OpenClaw dispatch.sh(兜底,Claude -p) ← 复杂任务,贵
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
| 主后端 | [Hermes](https://github.com/nous-research/hermes) | `hermes chat -q ... -Q --yolo` |
| 兜底 | [OpenClaw Lite](https://github.com/xinnan-tech/openclaw-lite) + Claude `-p` | `~/.openclaw/lite/bin/dispatch.sh` |

---

## 快速开始(首次接入 0→1)

### 0. 前置环境

- macOS arm64(M 系列)或 Linux
- [uv](https://github.com/astral-sh/uv) — Python 版本和包管理
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```
- 一个 OpenAI 兼容 + 支持 function_call 的 LLM(gpt-4/gpt-5 系、Qwen、DeepSeek v3 都行)
- (可选)Hermes CLI — 作为"免费工具派发后端",详见下面
- (可选)OpenClaw Lite — 作为"强力兜底",详见下面

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

### 3. 填 LLM api_key

编辑 `data/.config.yaml`,找到 `LLM.Gpt54LLM`:

```yaml
LLM:
  Gpt54LLM:
    type: openai
    model_name: gpt-5.4                       # 换成你的模型
    base_url: https://api.86gamestore.com/v1  # 换成你的 base_url
    api_key: YOUR_OPENAI_COMPATIBLE_API_KEY   # ⚠️ 必填
```

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
python3 test_client.py list                                # 列出 4 个 MCP 工具
python3 test_client.py call list_agents                    # 应返回 agent 列表

# ② 端到端 WebSocket(模拟小智设备发文字)
python3 test_xiaozhi_ws.py "列出所有可用的 agent"
python3 test_xiaozhi_ws.py "读今天的日报"
python3 test_xiaozhi_ws.py "派 planner 用一句话总结今天最紧急的 3 件事"

# ③ 真麦克风语音
python3 -m http.server 8006 --directory \
  repo/main/xiaozhi-server/test &
open http://localhost:8006/test_page.html
# 设置 → OTA 地址填: http://127.0.0.1:8003/xiaozhi/ota/
```

---

## 接入 Hermes(可选,作为主路后端)

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

dispatcher 会自动识别 `~/.local/bin/hermes`,在 `dispatch_agent` 调用时优先走 Hermes。如果 Hermes 失败(超时/异常)会自动回落到 OpenClaw 的 Claude。

---

## 接入 OpenClaw Lite(可选,作为强力兜底 + 提供 agent 身份)

OpenClaw Lite 是自建的 launchd + `claude -p` 调度系统,提供 7 个角色 agent(main / planner / site-ops / support / overseas-dev / designer / keyword-miner)。

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

如果你不装完整 OpenClaw,可以手写一份最小 `~/.openclaw/lite/agents.json` 让 `list_agents` 和 `dispatch_agent(... via Hermes)` 工作:

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

没有 `dispatch.sh` 时,`dispatch_agent` 全部走 Hermes;没有日报文件时 `read_daily_report` 会返回空目录提示。

---

## MCP 工具(dispatcher 暴露)

`http://127.0.0.1:9000/mcp` 暴露 4 个工具:

| 工具 | 用途 | 调用路径 |
|------|------|---------|
| `list_agents()` | 列出 agent | 读 `~/.openclaw/lite/agents.json` |
| `dispatch_agent(agent_id, task)` | 派发任务 | Hermes 主路 → Claude 兜底 |
| `query_agent_status()` | 查最近一次任务 | 读 `/tmp/xiaozhi-dispatcher-state.json` |
| `read_daily_report(date)` | 读日报 | 读 `~/.openclaw/workspace/logs/daily/*.md` |

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
│   └── .mcp_server_settings.json # MCP 接入点:指向 127.0.0.1:9000
├── models/SenseVoiceSmall/       # ASR 模型(模型文件 .gitignore)
├── dispatcher/                   # 自研 MCP server
│   ├── server.py                 # 4 个 MCP 工具
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
2. **`tool_call_timeout: 90`** — `.config.yaml` 里默认 90s。默认 30s 对 Hermes 不够(Hermes 冷启动 10s+)。
3. **SOCKS 代理会干扰 httpx** — `start.sh` 已 unset 所有代理变量。如果你自己起 dispatcher,记得先 `unset ALL_PROXY HTTPS_PROXY HTTP_PROXY`。
4. **首轮 MCP 竞态** — 改了 `core/connection.py` 7 行,见上面「修补小智源码」。
5. **prompt 里必须列出工具名** — LLM 拿到 `tools=[...]` 但偶尔会幻觉"没这功能",所以在 system prompt 里明确罗列工具 + 路由规则,成功率接近 100%。

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
A: 可以。只要一个最简 `agents.json`(见上面),`dispatch_agent` 就能全走 Hermes 了。

**Q: 可以不要 Hermes 吗?**
A: 可以。`dispatch.sh` 会直接兜底。但你需要装完整 OpenClaw Lite 并有 Claude CLI 授权。

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
- OpenClaw Lite — 按各自 license
