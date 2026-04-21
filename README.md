# CodePower AI — 语音版 Hermes 执行助手

把一个可语音驱动的 `Hermes` 执行链接到小智服务上。一句话说“让 Hermes 去做 XXX”，小智就会识别请求、先进入确认链，再通过 MCP 调起 Hermes 落地执行,最后用 EdgeTTS 语音播报结果。

**硬件目标**:装在充电宝里的随身执行助手(ESP32 + 麦克风)。黑客松期间用浏览器模拟麦克风演示。

```
麦克风/浏览器
   │  WebSocket(opus)
   ▼
xiaozhi-esp32-server(8000 / 8003)
   │  MCP streamable-http
   ▼
dispatcher(127.0.0.1:9000)       ← 本仓库核心代码
   │
   └── Hermes(主路,gpt-5.4 / OpenAI 兼容) ← 当前唯一暴露给模型的执行工具
```

---

## 技术栈

| 层 | 选型 | 说明 |
|------|------|------|
| 运行环境 | Python 3.10 venv(uv 管理)| ARM64 原生,Docker Rosetta 太慢不用 |
| ASR | OpenAI ASR | 当前默认 `gpt-4o-mini-transcribe` |
| LLM | OpenAI 官方接口 + function_call | 当前默认 `gpt-5.4` |
| Intent | function_call | 复用主 LLM,不另起模型 |
| TTS | EdgeTTS | 免费,zh-CN-XiaoxiaoNeural 女声 |
| MCP | streamable-http(`mcp>=1.22`) | 官方 Python SDK |
| 主后端 | [Hermes](https://github.com/nous-research/hermes) | `hermes chat -q ... -Q --yolo` |

---

## 当前实现

当前这套仓库默认跑的是宿主机 Python 服务,不是 Docker 主流程:

- `xiaozhi-server`: `0.0.0.0:8000` / `0.0.0.0:8003`
- `dispatcher`: `127.0.0.1:9000`
- 测试页静态服务: `http://localhost:8006/test_page.html`

当前已经落地的核心能力:

- 只暴露 1 个 MCP 工具: `hermes_repo_task(task)`
- 用户明确点名 `Hermes` / `Hummus` 时,server 会直接进入确认链,不再依赖模型首轮自己猜工具调用
- 决策型请求新增 `pending_proposal` 会话态,必须先“采纳 / 拒绝”,确认后才真正执行 Hermes
- 测试页新增“接受 / 拒绝”按钮,进入待确认态时会高亮,并插入待确认卡片
- Hermes 默认工作目录固定为 `/Users/carlos_chen/Desktop/work_space/hemers_work_dir`
- Hermes 工具超时和小智 `tool_call_timeout` 已统一为 `300s`
- `xiaozhi-server` 监听 `0.0.0.0`,同一局域网设备可通过宿主机 IP 访问 OTA

适合的请求类型不只限写代码,也包括:

- 读写文件
- 分析仓库
- 生成文档
- 整理目录
- 执行明确的工程类任务

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

### 3. 填 LLM / ASR api_key

编辑 `data/.config.yaml`,当前至少需要检查这两段:

```yaml
LLM:
  Gpt54LLM:
    type: openai
    model_name: gpt-5.4
    base_url: https://api.openai.com/v1
    api_key: YOUR_OPENAI_API_KEY

ASR:
  OpenaiASR:
    type: openai
    api_key: YOUR_OPENAI_API_KEY
    base_url: https://api.openai.com/v1/audio/transcriptions
    model_name: gpt-4o-mini-transcribe
```

如果你要换成别的 OpenAI 兼容接口,改 `base_url` 和模型名即可。

### 4. 启动

```bash
./scripts/start.sh
# 看日志: ./scripts/logs.sh
# 停止:   ./scripts/stop.sh
```

`scripts/start.sh` 现在已经补了 `nohup ... < /dev/null`,后台启动更稳定。

### 5. 测试

先起测试页:

```python
python3 -m http.server 8006 --directory repo/main/xiaozhi-server/test
```

打开:

- `http://localhost:8006/test_page.html`

测试页连接参数:

- `OTA服务器地址`: `http://127.0.0.1:8003/xiaozhi/ota/`
- `WebSocket服务器地址`: 可留空,通常会由 OTA 自动回填

如果要让同一 Wi-Fi 下的其它硬件访问:

- 把 `server.ip` 设成 `0.0.0.0`
- 把 `server.websocket` 和 `server.vision_explain` 保留为带“你的局域网IP”的占位格式
- OTA 会自动按当前宿主机局域网 IP 下发 WebSocket 地址
- 例如宿主机 IP 是 `192.168.1.6` 时,OTA 地址就是 `http://192.168.1.6:8003/xiaozhi/ota/`
- 如果宿主机开着 VPN、代理或虚拟网卡,自动识别的 IP 可能不对,这时直接把 `server.websocket` 和 `server.vision_explain` 改成真实 Wi-Fi IP

推荐直接测试这条最小闭环:

1. 说一句明确点名 Hermes 的话,例如:
   `让 Hummus 在当前工作目录生成一份目录说明`
2. 页面应出现 proposal 文案
3. “接受 / 拒绝”按钮应高亮
4. 点“接受”后才真正执行 Hermes
5. 执行结果会继续在页面上显示并播报

### 6. 验证 dispatcher

```bash
cd dispatcher
source .venv/bin/activate

# dispatcher 自身(不经过小智)
python3 test_client.py list
```

---

## 接入 Hermes

Hermes 是当前唯一暴露给模型的执行工具。

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

## MCP 工具(dispatcher 暴露)

`http://127.0.0.1:9000/mcp` 当前只暴露 1 个工具:

| 工具 | 用途 | 调用路径 |
|------|------|---------|
| `hermes_repo_task(task)` | 让 Hermes 在固定工作目录执行任务 | `Hermes CLI → /Users/carlos_chen/Desktop/work_space/hemers_work_dir` |

想加新工具?在 `dispatcher/server.py` 加一个 `@mcp.tool()` 即可,小智会自动拿到。

---

## 确认链路

当前所有显式点名 `Hermes` 的请求都走“先提案、后执行”的状态机:

1. ASR 把语音转成文本
2. server 命中“让/叫/交给 Hermes”规则
3. 生成 `pending_proposal`
4. 前端收到 proposal 结构化消息,高亮“接受 / 拒绝”
5. 用户点击“接受”后,server 才真正调用 `hermes_repo_task`
6. 用户点击“拒绝”后,清空 proposal,返回“已取消”

这部分逻辑主要分布在:

- `repo/main/xiaozhi-server/core/handle/proposalHandler.py`
- `repo/main/xiaozhi-server/core/handle/intentHandler.py`
- `repo/main/xiaozhi-server/test/test_page.html`
- `repo/main/xiaozhi-server/test/js/ui/controller.js`
- `repo/main/xiaozhi-server/test/js/core/network/websocket.js`

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
│   ├── server.py                 # 只暴露 hermes_repo_task
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
