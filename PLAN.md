# 小智语音接入 OpenClaw/Hermes — 黑客松方案

**项目目标:** 语音说"派 planner 查今天任务" → 小智识别 → 调 MCP → 调度 OpenClaw/Hermes agent 执行 → 语音播报结果
**时间:** 2 天
**部署:** Mac 本地(`~/xiaozhi-hackathon/`) — 源码直跑(Docker Rosetta 太慢不可用)

---

## 1. 架构

```
┌─────────────────────────────────────────────────┐
│ 网页/ESP32(麦克风)                               │
└──────────────────┬──────────────────────────────┘
                   │ WebSocket (Opus 编码)
                   ▼
┌─────────────────────────────────────────────────┐
│ xiaozhi-server (Python 3.10 源码, 端口 8000)     │
│  ├─ ASR: FunASR 本地(免费)                       │
│  ├─ LLM: gpt-5.4 via 86gamestore(兼容 OpenAI)   │
│  ├─ Intent: Function Call                       │
│  └─ TTS: EdgeTTS(免费,微软)                      │
└──────────────────┬──────────────────────────────┘
                   │ MCP WebSocket (端口 8004)
                   ▼
┌─────────────────────────────────────────────────┐
│ dispatcher MCP Server (Python, 自研)             │
│  暴露工具给 LLM:                                  │
│  ├─ dispatch_openclaw(agent_id, task)  → Claude │
│  ├─ dispatch_hermes(task)              → gpt-5.4│
│  ├─ query_agent_status(run_id)                  │
│  └─ list_agents()                               │
└──────┬────────────────────────┬─────────────────┘
       │                        │
       ▼                        ▼
┌──────────────┐         ┌──────────────┐
│ OpenClaw     │         │ Hermes       │
│ dispatch.sh  │         │ hermes chat  │
│ (Claude -p)  │         │ (gpt-5.4)    │
└──────────────┘         └──────────────┘
```

---

## 2. 技术选型(全免费)

| 组件 | 选型 | 理由 |
|------|------|------|
| 运行 | Python 3.10 venv(uv 管理) | ARM64 原生,Docker 在 Mac 太慢 |
| ASR | FunASR/SenseVoiceSmall(本地) | 免费,中文好,首次下 1G 模型 |
| LLM | gpt-5.4 via 86gamestore | 已有 key,免费/便宜 |
| TTS | EdgeTTS | 免费,微软声线,质量足够演示 |
| VAD | Silero(内置) | 默认 |
| MCP | Python `mcp` SDK | 官方 SDK,最省事 |

**演示设备:** 用小智官方 **web demo**(浏览器录音)模拟,无需 ESP32。

---

## 3. 文件结构

```
~/xiaozhi-hackathon/
├── PLAN.md                    # 本文档
├── README.md                  # 快速启动指南
├── docker-compose.yml         # 小智 server 容器
├── data/                      # 小智 data 目录
│   └── .config.yaml           # 小智主配置
├── models/                    # ASR 模型(首次下载)
├── dispatcher/                # 自研 MCP server
│   ├── server.py              # MCP server 主程序
│   ├── tools.py               # 工具实现
│   ├── requirements.txt       # mcp, websockets
│   └── .env                   # MCP 接入点 token
├── scripts/
│   ├── start.sh               # 一键启动
│   ├── stop.sh                # 一键停止
│   ├── logs.sh                # 查日志
│   └── test-voice.sh          # 测试脚本
└── demo/
    └── demo-script.md         # 黑客松演示脚本
```

---

## 4. MCP Server 设计

### 4.1 暴露的工具(Hermes 主路,Claude 兜底)

```python
@tool
def list_agents() -> str:
    """列出所有可用的 OpenClaw agent 及其职责"""

@tool
def dispatch_agent(agent_id: str, task: str) -> str:
    """主派发入口 — 默认走 Hermes(gpt-5.4,免费),Hermes 失败才回落 Claude
    agent_id: 只作为"角色 prompt"提示词(main/planner/site-ops/...),不限制执行后端
    task: 任务描述(自然语言)
    返回: 执行结果摘要
    """

@tool
def query_agent_status() -> str:
    """查询最近一次派发的 agent 执行状态"""

@tool
def read_daily_report(date: str = "today") -> str:
    """读 OpenClaw 日报,避免每次派 agent"""
```

**执行策略:**
1. 首选 `hermes chat --message "<身份 prompt> + <task>" --yolo`
2. Hermes 异常(超时/错误/返回空)→ 自动降级到 `~/.openclaw/lite/bin/dispatch.sh <agent_id> "<task>"`
3. 都失败才报错

### 4.2 实现要点
- 用 Python `mcp` SDK 的 WebSocket 传输
- 通过 `ws://host:8004/mcp_endpoint/mcp/?token=<TOKEN>` 接入小智
- dispatch_openclaw 调用 `~/.openclaw/lite/bin/dispatch.sh`
- dispatch_hermes 调用 `hermes chat --message "<task>" --yolo`(非交互)
- 为避免语音等待过久,长任务用 **异步派发**,返回"已派发,请稍后问状态"
- 短查询(list_agents, read_daily_report)同步返回

---

## 5. xiaozhi-server 配置要点

### 5.1 LLM(改成 86gamestore)
```yaml
selected_module:
  LLM: ChatGLMLLM  # 用兼容 OpenAI 接口的 provider,名字不重要
LLM:
  ChatGLMLLM:
    type: openai
    model_name: gpt-5.4
    base_url: https://api.86gamestore.com/v1
    api_key: YOUR_OPENAI_COMPATIBLE_API_KEY
```

### 5.2 ASR
```yaml
selected_module:
  ASR: FunASR
ASR:
  FunASR:
    model_dir: models/SenseVoiceSmall  # 首次自动下载
    output_dir: tmp/
```

### 5.3 TTS
```yaml
selected_module:
  TTS: EdgeTTS
TTS:
  EdgeTTS:
    voice: zh-CN-XiaoxiaoNeural  # 女声
```

### 5.4 MCP 接入点
```yaml
# 启用 MCP endpoint,小智作为 server,我们的 dispatcher 作为 client 连过去
mcp_endpoint:
  enabled: true
  token: hackathon-local-token-xxx  # 自定义
```

---

## 6. 分步任务清单

| # | 任务 | 预计耗时 | 验收标准 |
|---|------|---------|---------|
| 1 | 环境准备:Docker Desktop 运行,clone 小智仓库 | 15min | `docker ps` 能跑 |
| 2 | 起小智 server(最简化安装) | 30min | websocket 8000 可连 |
| 3 | 改 config.yaml(LLM→86gamestore, TTS→EdgeTTS) | 15min | 日志无报错 |
| 4 | web demo 测试纯对话(无 MCP) | 15min | 能说话、能回答 |
| 5 | 写 dispatcher MCP server(最小版) | 1.5h | 本地 `python server.py` 能启 |
| 6 | 配 MCP 接入点,dispatcher 连进去 | 30min | 小智日志打出 "MCP tools registered: [...]" |
| 7 | 端到端联调:语音→派 agent→结果播报 | 1h | 说"列出可用 agent" 能听到名单 |
| 8 | Hermes 主路 + Claude 兜底降级逻辑 | 1h | 主路通,模拟 Hermes 故障能自动落 Claude |
| 9 | 异步派发 + 状态查询 + 内部测试 | 1.5h | 3 个 MVP 指令全跑通,录屏 |
| 10 | 黑客松演示脚本 + 彩排 | 30min | 流畅跑通 3 个示例指令 |

### 内部测试约束(每阶段必做)
- **任务 2 完成**:curl WebSocket 握手成功
- **任务 4 完成**:至少 5 轮对话无错
- **任务 5 完成**:`mcp-inspector` 或手写 client 列工具正常
- **任务 7 完成**:连续说 3 次"列出 agent",3 次都正确
- **任务 8 完成**:手动 kill Hermes 进程,验证自动回落 Claude
- **任务 9 完成**:全流程跑 3 遍 MVP 指令无卡顿、无报错

**总计:** ~7 小时核心工作 + 调试 buffer 1 天

---

## 7. 演示指令清单(MVP 目标)

| 语音 | 调用 | 预期回复 |
|------|------|---------|
| "小智,列出所有 agent" | `list_agents()` | "有 main、planner、site-ops..." |
| "让 planner 看看今天有什么任务" | `dispatch_agent('planner', ...)` → Hermes | "已派发,约 30 秒出结果" |
| "查一下日报" | `read_daily_report('today')` | 读出 `~/.openclaw/workspace/logs/daily/YYYY-MM-DD.md` 摘要 |
| "刚才那个任务做完了吗" | `query_agent_status()` | "planner 还在执行,已用时 30 秒" |

---

## 8. 风险与应对

| 风险 | 概率 | 应对 |
|------|------|------|
| FunASR 首次下载模型慢 | 高 | 提前下好,或改用云端免费 ASR |
| Docker 在 Mac arm64 需本地编译 | 中 | 用官方 compose,如果镜像拉不下来就本地 build |
| MCP 接入点配置繁琐 | 中 | 严格按官方 docs/mcp-endpoint-integration.md |
| 语音识别同音字误判 agent 名 | 中 | 在 system prompt 里加 agent 列表,让 LLM 模糊匹配 |
| 网页 demo 麦克风权限 | 低 | 用 http://localhost(不需要 https) |
| 演示现场网络差 | 中 | 带手机热备,LLM 调用依赖公网 |

---

## 9. 黑客松亮点话术

- **"我把一个多 agent 运营系统接到了语音" — 从 GUI/终端进化到对话界面**
- **全本地部署,隐私可控,无云端依赖(除 LLM 调用)**
- **双 agent 后端:Claude(质量)+ gpt-5.4(成本),LLM 自动路由**
- **基于 MCP 协议,可无限扩展工具**(举例:说"帮我发个推特"就能接 Twitter MCP)

---

## 10. 下一步(执行前确认)

- [ ] 确认部署在 Mac 本地(非 CloudStudio)
- [ ] 确认 LLM 用 86gamestore/gpt-5.4(省钱方案)
- [ ] 确认 MCP 双路径(OpenClaw + Hermes 都接)
- [ ] 确认演示指令清单的前 3 个作为 MVP

以上确认后开始执行任务 1-4(安装 + 配置),通了再做 5-10。
