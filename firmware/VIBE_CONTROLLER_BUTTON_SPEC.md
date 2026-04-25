# Vibe Coding 控制器按键规范

## 目的

本文档用于定义 `1.54TFT WiFi` 设备在作为 vibe coding 控制器时的目标按键行为。

目的有两个：

- 给后续 agent 一个明确、稳定的实现目标
- 避免后续修改时对按键语义产生歧义

## 目标开发板

当前参考开发板实现文件：

- `main/boards/xingzhi-cube-1.54tft-wifi/xingzhi-cube-1.54tft-wifi.cc`

当前 `config.h` 中的 GPIO 定义：

- `BOOT_BUTTON_GPIO = GPIO_NUM_0`
- `VOLUME_UP_BUTTON_GPIO = GPIO_NUM_40`
- `VOLUME_DOWN_BUTTON_GPIO = GPIO_NUM_39`

## 目标交互行为

### 按键 1：主键 / BOOT

- 短按：切换到下一个 agent
- 按下并保持：开始录音 / 开始监听
- 松开：结束录音 / 结束监听，并发送本次语音输入

### 按键 2：上侧按键

- 短按：采纳当前建议

### 按键 3：下侧按键

- 短按：拒绝当前建议

## 产品语义

这个控制器应当被设计成一个“小型语音输入 + 决策确认”设备。

推荐角色分工如下：

- 按键 1：输入控制和 agent 切换
- 按键 2：正向动作
- 按键 3：负向动作

这样设计的原因：

- 一个主键负责切换对象和语音输入
- 一个键负责确认/采纳
- 一个键负责拒绝/取消

三者职责清晰，不容易混淆。

## 推荐的服务端事件名

建议服务端统一使用简洁、明确的英文动作名，而不是使用含义模糊的命名。

推荐事件名：

- `switch_agent`
- `start_record`
- `stop_record`
- `accept`
- `reject`

建议事件示例：

```json
{"event":"switch_agent","direction":"next"}
{"event":"start_record"}
{"event":"stop_record"}
{"event":"accept"}
{"event":"reject"}
```

## 推荐传输方式

当前仓库已经具备设备主动向服务端发送 MCP 风格消息的能力，已有通路包括：

- `Application::SendMcpMessage(...)`
- `Protocol::SendMcpMessage(...)`

推荐原则：

- 纯本地设备动作才留在本地执行
- 与业务状态相关的按键行为尽量上报给 server
- agent 切换、建议状态、采纳/拒绝等逻辑尽量由服务端统一编排

也就是说，这个控制器更适合做成“事件上报型”，而不是把业务规则硬编码在固件里。

## 状态约束

为了避免交互冲突，建议使用下面这套规则。

### 按键 1 短按

- 仅在设备处于 `idle` 状态时有效
- 动作：发送 `switch_agent`
- 如果设备本地维护了当前 agent 状态，可以同步在屏幕上显示当前 agent 名称

### 按键 1 长按说话

- 在 `press down` 时：
  - 如果当前设备处于 `speaking`，先中断当前播报
  - 然后开始监听 / 开始录音
  - 如果服务端需要显式追踪录音状态，则发送 `start_record`

- 在 `press up` 时：
  - 停止监听 / 停止录音
  - 发送 `stop_record`

### 按键 2 短按

- 发送 `accept`
- 在控制器模式下，不再映射为本地音量或亮度功能

### 按键 3 短按

- 发送 `reject`
- 在控制器模式下，不再映射为本地音量、静音或亮度功能

## 推荐固件绑定方式

当前这块板子已经在使用：

- `OnClick(...)`
- `OnLongPress(...)`

但对于“按住录音”这种交互，推荐按键 1 改为：

- `OnClick(...)`：用于 `switch_agent`
- `OnPressDown(...)`：用于 `start_record`
- `OnPressUp(...)`：用于 `stop_record`

原因：

- “按住说话”更适合用按下/松开建模，而不是只依赖 `OnLongPress(...)`
- 可以更精确地控制开始和结束边界
- 更符合 PTT（push-to-talk）交互习惯

按键 2 和按键 3 则继续使用：

- `OnClick(...)`

## 推荐本地处理逻辑

### 按键 1 短按

- 检查当前设备状态
- 如果不是 `idle`，则忽略或者延后处理
- 发送 `switch_agent`

### 按键 1 按下

- 如果设备处于省电状态，先唤醒
- 如果当前正在播报，先执行 `AbortSpeaking(...)`
- 调用 `StartListening()`
- 按需发送 `start_record`

### 按键 1 松开

- 调用 `StopListening()`
- 按需发送 `stop_record`

### 按键 2 短按

- 发送 `accept`

### 按键 3 短按

- 发送 `reject`

## 当前实现与目标实现的差距

当前 `1.54TFT WiFi` 板还没有进入控制器模式。

当前行为是：

- 按键 1 短按：切换聊天状态，或者在启动阶段重新进入 Wi-Fi 配网
- 按键 2 短按：音量加
- 按键 2 长按：最大音量
- 按键 3 短按：音量减
- 按键 3 长按：静音

如果切换到 vibe coding 控制器模式，这一套本地音量语义应当整体替换掉。

## 推荐的 MCP / 事件封装格式

如果走 MCP 通道，建议增加一个统一的按键事件封装。

例如：

```json
{
  "method": "notify/button_event",
  "params": {
    "board": "xingzhi-cube-1.54tft-wifi",
    "event": "accept"
  }
}
```

如果直接对接当前 `xiaozhi-server` 的确认链,更推荐直接发送文本消息:

```json
{"type":"accept"}
{"type":"reject"}
```

切换 agent：

```json
{
  "method": "notify/button_event",
  "params": {
    "board": "xingzhi-cube-1.54tft-wifi",
    "event": "switch_agent",
    "direction": "next"
  }
}
```

开始录音：

```json
{
  "method": "notify/button_event",
  "params": {
    "board": "xingzhi-cube-1.54tft-wifi",
    "event": "start_record"
  }
}
```

结束录音：

```json
{
  "method": "notify/button_event",
  "params": {
    "board": "xingzhi-cube-1.54tft-wifi",
    "event": "stop_record"
  }
}
```

## 给后续 agent 的实现注意事项

- 不要在控制器模式下继续保留旧的音量按键语义
- 按键 1 的录音行为优先使用 `OnPressDown` 和 `OnPressUp`
- 保持交互模型简单、可预测
- 如果服务端是权威状态源，不要在设备侧重复维护过多业务状态
- 如果为了 UI 反馈需要本地状态，尽量只保留最少状态，例如当前 agent 名称

## 推荐下一步

建议后续直接把这份规范落实到：

- `main/boards/xingzhi-cube-1.54tft-wifi/xingzhi-cube-1.54tft-wifi.cc`

后续可选工作：

- 增加一个统一的按钮事件上报辅助函数
- 增加当前 agent 的本地显示提示
- 增加“聊天模式 / 控制器模式”的编译开关或运行时开关
