# PowCoder 前端任务可视化技术方案

## 背景与目标

PowCoder 当前已经具备两类核心交互:

- **闲聊模式**: 前端切到 `chat` 后,小智服务端直接走 `JoyInsideLLM`,不进入 function call 和工具链。
- **任务模式**: 前端切到 `task` 后,小智服务端走 GPT/function_call,先生成工具调用提案,用户采纳后再执行 Hermes、OpenClaw、Codex、Claude Code、邮件等工具。

硬件接入后,需要一个独立前端页面展示"设备正在闲聊"还是"正在执行任务",以及任务由哪个 agent / 后端执行、当前执行状态、执行完成结果。这个页面不是给最终用户聊天用,而是给演示和调试使用,用于实时观察运行效果。

参考原型图的核心结构:

- 左侧: session history,区分闲聊 session 和任务 session。
- 中间: 当前会话画布,闲聊时展示 JoyInside/陪伴服务,任务时展示 agent / Hermes / Claude Code / Codex 等工作卡片。
- 右侧: 可选 agent/worker 状态池,展示空闲、执行中、已完成、失败等状态。

## 当前代码现状

### 运行链路

```text
浏览器/硬件麦克风
  -> xiaozhi-server WebSocket :8000
  -> xiaozhi-server task/chat mode
  -> dispatcher MCP :9001
  -> Hermes / OpenClaw dispatch.sh / Codex CLI / Claude Code CLI / Resend
```

关键文件:

- `repo/main/xiaozhi-server/test/test_page.html`: 当前浏览器测试页面。
- `repo/main/xiaozhi-server/test/js/ui/controller.js`: 已有模式切换、聊天流、采纳/拒绝按钮。
- `repo/main/xiaozhi-server/test/js/core/network/websocket.js`: 发送 `listen` 消息时携带 `mode: auto|chat|task`,接收 `proposal` 状态。
- `repo/main/xiaozhi-server/core/connection.py`: `chat` 模式走 JoyInside,`task` 模式走 GPT/function_call。
- `repo/main/xiaozhi-server/core/handle/proposalHandler.py`: 所有工具调用先进入待确认 proposal。
- `dispatcher/server.py`: MCP 工具执行入口,当前已有部分文件状态写入。

### 状态能力

当前保留 dispatcher 的旧状态文件,同时新增统一可视化状态文件:

- `/tmp/xiaozhi-dispatcher-state.json`: 最近一次任务状态。
- `/tmp/xiaozhi-dispatcher-runs/{run_id}.json`: 已完成任务记录。
- `/tmp/powcoder-visualizer/state.json`: 前端读取的统一状态。
- `/tmp/powcoder-visualizer/events.jsonl`: 事件追加日志。
- `/tmp/powcoder-visualizer/sessions/{session_id}.json`: session 快照。

已写入状态的工具:

- `dispatch_agent(agent_id, task)`
- `hermes_repo_task(task)`
- `run_codex(task, workdir, allow_edits)`
- `run_claude_code(task, workdir, allow_edits)`
- `send_email(to, subject, body)`

后续新增的工程任务工具按同一个 `start_worker/finish_worker` 模式接入。

### 已有确认机制

任务模式下所有工具调用都走确认:

```text
用户输入任务
  -> GPT 生成 function_call
  -> proposalHandler.stage_pending_proposal
  -> WebSocket 下发 { type: "proposal", state: "pending" }
  -> 前端显示"采纳 / 拒绝"
  -> 用户采纳
  -> WebSocket 发送 { type: "accept" }
  -> 服务端执行工具
  -> WebSocket 下发 proposal accepted/completed
```

拒绝时:

```text
前端发送 { type: "reject" }
  -> 服务端清空 pending_proposal
  -> WebSocket 下发 { type: "proposal", state: "rejected" }
```

## 中转方案决策

### 决策

第一阶段采用**文件中转**:

```text
任务执行器 / dispatcher / xiaozhi-server
  -> 写状态文件
  -> PowCoder visual service 读取文件
  -> 前端页面轮询或 SSE 展示
```

这个方案不是严格实时,但实现成本低,不侵入 Hermes / Claude Code / Codex 内部协议,能快速验证演示效果。

### 为什么不直接改 Hermes / Claude Code 内部协议

- Hermes、Claude Code、Codex 都是外部 CLI 或独立执行器,直接改内部事件流成本高。
- 当前演示重点是"看起来正在执行、能看到结果",不是逐 token 展示。
- 文件中转能兼容本地、硬件、Cloudflare Tunnel 和未来部署。

### 写入位置

不要要求 Hermes 或 Claude Code 自己回调前端。统一在 PowCoder 侧 wrapper 写状态:

1. 命令启动前写 `running`。
2. 命令执行中如果能拿到阶段性信息,追加 `event`。
3. 命令结束后写 `success` 或 `failed`。
4. 最后一行同步更新前端可读 state,保证页面最终态正确。

## Session 定义

为避免和小智 WebSocket session 混淆,前端需要区分两类 session:

### 1. Conversation Session

小智连接级会话,来自 `ConnectionHandler.session_id`。

用途:

- 展示当前硬件/浏览器连接,其中 `auto` 也按普通对话同步到可视化页。
- 归档用户和助手的对话消息。
- 和 chat/task 模式切换关联。

### 2. Task Session

用户明确发起的一次任务执行。用户沟通中说的 "session 指执行的任务",这里落为 `task_session`。

例如:

- "让 Hermes 整理这个仓库"
- "让 Claude Code 修这个 bug"
- "派 planner 写一个方案"

每个 task session 必须有自己的 `run_id`,即使来自同一个 conversation session。

推荐 ID:

```text
chat_20260423_001
task_20260423_001
run_1713840000
hermes_1713840000
claude_code_1713840000
codex_1713840000
```

## 状态模型

### 顶层状态文件

建议新增统一状态文件:

```text
/tmp/powcoder-visualizer/state.json
/tmp/powcoder-visualizer/events.jsonl
/tmp/powcoder-visualizer/sessions/{session_id}.json
```

第一阶段也可以兼容读取现有:

```text
/tmp/xiaozhi-dispatcher-state.json
/tmp/xiaozhi-dispatcher-runs/*.json
```

推荐 `state.json`:

```json
{
  "version": 1,
  "updated_at": "2026-04-23T12:00:00+08:00",
  "active_conversation_id": "websocket_session_id",
  "active_task_id": "task_20260423_001",
  "mode": "task",
  "connection": {
    "device_id": "web_test_client",
    "source": "browser|hardware|mqtt",
    "status": "connected"
  },
  "chat": {
    "provider": "JoyInside",
    "status": "idle|serving|failed",
    "last_user_text": "闲聊一下",
    "last_assistant_text": "..."
  },
  "proposal": {
    "state": "none|pending|accepted|rejected|completed",
    "function_name": "Hermes",
    "task": "整理项目",
    "proposal_text": "方案：用 Hermes 处理「整理项目」。采纳还是拒绝？"
  },
  "workers": [
    {
      "worker_id": "hermes_main",
      "kind": "hermes|openclaw|claude_code|codex|joyinside|email",
      "display_name": "Hermes agent",
      "agent_id": "planner",
      "status": "idle|pending|running|success|failed|rejected",
      "task": "整理项目",
      "run_id": "hermes_1713840000",
      "started_at": "2026-04-23T12:00:00+08:00",
      "finished_at": null,
      "last_message": "正在执行",
      "result_preview": ""
    }
  ],
  "sessions": [
    {
      "session_id": "task_20260423_001",
      "type": "task",
      "title": "让 Hermes 整理项目",
      "status": "running",
      "created_at": "2026-04-23T12:00:00+08:00"
    }
  ]
}
```

### 事件文件

`events.jsonl` 用于前端增量刷新:

```jsonl
{"seq":1,"ts":"2026-04-23T12:00:00+08:00","event":"conversation.started","conversation_id":"...","payload":{"mode":"task"}}
{"seq":2,"ts":"2026-04-23T12:00:03+08:00","event":"proposal.pending","task_id":"task_20260423_001","payload":{"function_name":"Hermes","task":"整理项目"}}
{"seq":3,"ts":"2026-04-23T12:00:05+08:00","event":"proposal.accepted","task_id":"task_20260423_001","payload":{}}
{"seq":4,"ts":"2026-04-23T12:00:06+08:00","event":"worker.running","task_id":"task_20260423_001","payload":{"worker_id":"hermes_main","backend":"hermes"}}
{"seq":5,"ts":"2026-04-23T12:01:10+08:00","event":"worker.success","task_id":"task_20260423_001","payload":{"result_preview":"已完成..."}}
```

事件只记录摘要,不要写入完整密钥、完整邮件正文、token、私有文件内容。

## 状态颜色规范

前端统一按 `status` 映射颜色,不要让各执行器自己决定颜色。

| 状态 | 颜色 | 用途 |
|------|------|------|
| `idle` | 黑色或深灰 | 未运行、空闲、正常待命 |
| `pending` | 橙色 | 待用户确认 |
| `accepted` | 蓝色浅态 | 已采纳,准备执行 |
| `running` | 蓝色 | 正在运行。Hermes、Claude Code、Codex、OpenClaw 正在工作时都用蓝色 |
| `success` | 绿色 | 执行成功。可在 3 秒后降级成黑色正常态 |
| `failed` | 红色 | 执行失败 |
| `rejected` | 深灰 | 用户拒绝 |
| `canceled` | 深灰 | 被取消或被新任务打断 |

原型图映射:

- 红色卡片: 执行中或异常需要关注。建议最终规范里执行中改成蓝色,失败保留红色。
- 蓝色卡片: 已完成或当前选中。建议已完成用绿色/黑色,蓝色只表示 running。
- 绿色卡片: 空闲可用或成功完成。若同时存在 success 和 idle,绿色优先给 success,空闲用黑色/灰色。

## 前端页面设计

### 页面布局

```text
+-------------------------------------------------------------+
| PowCoder                                                    |
|                                                             |
| +-------------------+  +-------------------------------+    |
| | session history   |  | 当前状态画布                  |    |
| | - session-闲聊    |  |                               |    |
| | - session-任务xxx |  | 闲聊: JoyInside 服务卡片      |    |
| |                   |  | 任务: agent / worker 卡片     |    |
| +-------------------+  +-------------------------------+    |
|                                                             |
|                           右侧可选 worker pool / legend     |
+-------------------------------------------------------------+
```

### 左侧 session history

展示最近 N 条 session:

- 闲聊 session: `chat` 图标,标题来自首条用户消息。
- 任务 session: `task` 图标,标题来自任务摘要。
- 状态点:
  - 蓝色: 正在执行。
  - 绿色: 已完成。
  - 红色: 失败。
  - 灰色: 闲聊或已取消。

点击 session 后,中间画布切换到该 session 的详情。

### 中间当前状态画布

#### 闲聊状态

显示:

- 大标题: `闲聊一下`
- 主服务卡片: `JoyInside`
- 状态: `服务中 / 空闲 / 失败`
- 最近一轮 user / assistant 摘要

闲聊模式不显示 Hermes / Claude Code / Codex 卡片,避免误解为任务执行。

#### 任务状态

显示:

- 大标题: `执行任务`
- 当前 proposal 卡片:
  - function_name
  - task
  - proposal_text
  - `采纳 / 拒绝` 状态
- worker 卡片:
  - Hermes agent
  - OpenClaw agent
  - Claude Code
  - Codex
  - Resend Email

同一个任务可以有多个 worker,例如:

```text
planner agent -> Hermes
Claude Code -> 代码修改
send_email -> 通知结果
```

### 右侧 worker pool

可选展示所有可调用后端:

- JoyInside
- Hermes
- OpenClaw
- Claude Code
- Codex
- Email

每个卡片只展示当前状态和最近一次任务。这个区域不是任务详情,而是"资源池状态"。

## 后端服务设计

### 已新增服务

新增一个轻量服务:

```text
powcoder_visual_service
```

职责:

- 读取 `/tmp/powcoder-visualizer/state.json`
- 兼容读取 `/tmp/xiaozhi-dispatcher-state.json`
- 读取 `/tmp/powcoder-visualizer/events.jsonl`
- 提供 HTTP API 给前端
- 静态托管可视化页面

建议端口:

```text
http://127.0.0.1:9200
```

### API

```text
GET /api/state
GET /api/sessions
GET /api/sessions/{session_id}
GET /api/events?after_seq=123
```

第一阶段:

- `GET /api/state`: 前端 1 秒轮询。
- `GET /api/events`: 前端 1 秒轮询增量事件。

第二阶段:

- `GET /api/stream`: SSE 推送事件,减少轮询。

### 为什么不直接塞进 xiaozhi-server 测试页

可以复用现有测试页,但建议先做独立页面:

- 不影响当前语音测试页面。
- 不和 Live2D、音频、摄像头控制耦合。
- 未来部署到硬件旁边或 Cloudflare 时更容易。

稳定后再决定是否合并进 `repo/main/xiaozhi-server/test/test_page.html`。

## 状态写入点

### xiaozhi-server

已写入:

- conversation started / closed
- 当前 `client_listen_mode`
- STT user text
- LLM / JoyInside assistant text
- proposal pending / accepted / rejected / completed

现有可接入点:

- `send_proposal_message`
- `send_stt_message`
- TTS `sentence_start`
- `ConnectionHandler._chat_joyinside`
- `ConnectionHandler.chat`

### dispatcher

已写入:

- task started
- worker running
- worker success / failed
- result preview

现有可接入点:

- `_save_state`
- `dispatch_agent`
- `hermes_repo_task`
- `run_codex`
- `run_claude_code`
- `send_email`

建议把文件写入封装成统一模块:

```text
dispatcher/visual_state.py
```

核心方法:

```python
write_state(patch: dict) -> None
append_event(event: str, payload: dict) -> None
start_worker(kind: str, task: str, run_id: str, **meta) -> None
finish_worker(run_id: str, status: str, result: str) -> None
```

写文件时使用原子写:

```text
write state.tmp -> rename state.json
```

避免前端读到半截 JSON。

## 任务执行流程

### 闲聊模式

```text
前端 chat mode
  -> listen detect mode=chat
  -> xiaozhi handle_user_intent 跳过工具意图
  -> ConnectionHandler._chat_joyinside
  -> JoyInsideLLM
  -> TTS 播报
  -> visual state: chat.status=serving -> idle
```

页面表现:

- 左侧新增或更新闲聊 session。
- 中间显示 JoyInside 卡片蓝色服务中。
- 结束后卡片回到黑色/绿色正常态。

### 任务模式

```text
前端 task mode
  -> listen detect mode=task
  -> GPT/function_call
  -> proposal pending
  -> 前端显示确认
  -> 用户 accept
  -> dispatcher 执行对应工具
  -> visual state worker.running
  -> worker.success / worker.failed
  -> proposal completed
```

页面表现:

- 左侧新增任务 session。
- 中间显示 proposal 卡片。
- 采纳后对应 worker 卡片变蓝。
- 完成后 worker 卡片变绿或恢复黑色。
- 失败后 worker 卡片变红。

## 与 Hermes / POM / Prompt 的关系

这里不要求 Hermes 自身实时回写。推荐在 PowCoder 对 Hermes 的 wrapper 层写状态:

```text
hermes_repo_task()
  -> write running
  -> hermes chat -q ...
  -> write success/failed
```

如果后续要让 Hermes 分阶段输出,可以在 Hermes 对接文档或 prompt 中要求它在阶段结束后输出结构化 marker,例如:

```text
POWCODER_STAGE {"stage":"scan","status":"success","message":"已扫描仓库"}
POWCODER_STAGE {"stage":"edit","status":"running","message":"正在修改 README"}
```

dispatcher 捕获 stdout 后解析 marker,追加到 `events.jsonl`。这属于第二阶段增强,第一阶段不用依赖。

## 前端技术实现建议

### 目录建议

```text
powcoder_dashboard/
  index.html
  src/
    api.js
    state-store.js
    session-list.js
    status-canvas.js
    worker-card.js
    styles.css
```

或直接放在:

```text
repo/main/xiaozhi-server/test/powcoder_dashboard/
```

### 数据刷新

第一阶段:

```js
setInterval(async () => {
  const state = await fetch('/api/state').then(r => r.json())
  render(state)
}, 1000)
```

第二阶段:

```js
const es = new EventSource('/api/stream')
es.onmessage = event => applyEvent(JSON.parse(event.data))
```

### 组件状态

worker 卡片只接收结构化数据:

```ts
type WorkerCard = {
  worker_id: string
  display_name: string
  kind: string
  status: 'idle' | 'pending' | 'running' | 'success' | 'failed' | 'rejected' | 'canceled'
  task?: string
  result_preview?: string
}
```

颜色、动画、文案都在前端统一处理。

## 分阶段计划

### P0: 技术文档

- 明确状态协议。
- 明确 UI 原型和数据源。
- 明确文件中转优先。

### P1: 状态写入补齐

- 新增 `visual_state.py`。
- dispatcher 所有工具统一写 `running/success/failed`。
- xiaozhi proposal / chat mode 写入状态。
- 兼容现有 `/tmp/xiaozhi-dispatcher-state.json`。

### P2: PowCoder visual service

- 新增 HTTP 服务,读取状态文件。
- 提供 `/api/state`、`/api/sessions`、`/api/events`。
- 静态托管前端页面。

### P3: 前端页面

- 实现左侧 session history。
- 实现中间 chat/task 状态画布。
- 实现 worker card 和颜色状态。
- 实现 1 秒轮询。

### P4: 接入硬件演示

- 用硬件 device_id 作为连接来源。
- 展示硬件当前 session。
- 验证 task mode 的 proposal accept/reject。
- 验证 Hermes / Claude Code / Codex 任务卡片状态变化。

### P5: 实时增强

- `/api/stream` SSE。
- 事件增量渲染。
- Hermes 阶段 marker 解析。
- 多任务并发视图。

## 验收标准

第一版可接受标准:

- 打开页面能看到当前连接状态。
- 闲聊模式下只显示 JoyInside 服务卡片。
- 任务模式下能显示待确认 proposal。
- 点击采纳后,对应 Hermes / Claude Code / Codex / agent 卡片变为蓝色执行中。
- 任务完成后卡片变为绿色或黑色正常态。
- 任务失败后卡片变为红色。
- 左侧 session history 能看到至少最近 20 个任务。
- 页面刷新后仍能从文件恢复最近状态。

不要求第一版做到:

- 真正毫秒级实时。
- 展示 Claude Code/Codex 内部逐步日志。
- 多设备权限系统。
- 在线编辑 prompt 或工具配置。

## 风险与注意事项

- **并发任务覆盖**: 现有 `STATE_FILE` 只存最近一次任务,新方案需要 `sessions/{id}.json` 保留历史。
- **文件半写入**: 必须用临时文件 + rename 原子写。
- **敏感信息**: 状态文件只能写摘要,不能写 token、邮箱密钥、完整私有文件内容。
- **长任务超时**: 前端应显示已耗时,超过阈值变成 warning,但不要自动判失败。
- **命名统一**: 文档中统一使用 Hermes、OpenClaw、Claude Code、Codex、JoyInside。语音识别中的 Hummus / Hamas 都按 Hermes 处理。
- **颜色语义统一**: 蓝色只表示正在执行,红色只表示失败或异常,避免同一种颜色表达多个状态。
