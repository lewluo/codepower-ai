# 一个基于 MCP 的 ESP32 语音聊天机器人

（中文 | [English](README_en.md) | [日本語](README_ja.md)）

## 项目简介

这是一个基于 ESP-IDF 的 ESP32 端 AI 语音聊天机器人固件。设备侧提供语音唤醒、录音采集、音频编解码、屏幕/灯光/按键/电源管理、OTA 升级，以及设备端 MCP（Model Context Protocol）能力；云端可对接 ASR、LLM、TTS 和更多 MCP 工具，实现对话、控制和扩展能力。

项目核心流程大致如下：

1. 设备上电后初始化 NVS、事件循环、板级外设。
2. 启动音频服务、显示服务、网络协议栈和 MCP 服务。
3. 通过 `WebSocket` 或 `MQTT + UDP` 与服务端建立连接。
4. 设备侧完成唤醒词检测、音频采集和状态切换。
5. 服务端返回文本、音频或控制指令，设备执行播放、显示和本地工具调用。

## 当前仓库状态

- 工程类型：`ESP-IDF` C++ 固件工程
- 项目名：`xiaozhi`
- 当前版本号：`2.0.2`
- 最低 IDF 版本：`5.4.0`
- 支持芯片：`ESP32`、`ESP32-C3`、`ESP32-S3`、`ESP32-P4`
- 当前 `sdkconfig` 默认目标：`esp32s3`
- 当前 `sdkconfig` 默认板型：`bread-compact-wifi`
- 默认分区表：`partitions/v2/16m.csv`

注意：仓库内同时包含大量其他板型支持代码；真正参与编译的是 `menuconfig` 或对应板型 `config.json` 选择出来的那一个。

## 主要能力

- 离线唤醒词检测，支持多种唤醒实现
- 流式语音链路：采集、编码、上传、播放
- 双协议通信：`WebSocket` 或 `MQTT + UDP`
- 设备侧 MCP 工具调用
- 云端 MCP 扩展能力接入
- 屏幕显示、表情、状态提示
- LED、按键、电池和电源管理
- 资源包下载与应用
- 固件 OTA、版本检查和激活流程
- 多板型适配，覆盖 70+ 开源硬件

## 技术栈与关键依赖

- 框架：`ESP-IDF >= 5.4`
- 语言：`C++`
- 音频：
  - `espressif/esp-sr`
  - `78/esp-opus-encoder`
  - `espressif/esp_codec_dev`
- 显示：
  - `lvgl/lvgl`
  - `esp_lvgl_port`
  - 多种 `esp_lcd_*` 驱动
- 网络与外设：
  - `78/esp-wifi-connect`
  - `78/esp-ml307`
  - `espressif/button`
  - `espressif/led_strip`
- 资源与多媒体：
  - `espressif/esp_mmap_assets`
  - `espressif2022/image_player`

依赖定义见 [main/idf_component.yml](main/idf_component.yml)。

## 目录结构

```text
.
├── main/
│   ├── application.*          # 应用主流程、状态机、协议初始化、OTA/资源检查
│   ├── audio/                 # 音频服务、编解码器、唤醒词、调试器
│   ├── display/               # OLED/LCD/LVGL 显示与表情系统
│   ├── protocols/             # WebSocket、MQTT+UDP 协议实现
│   ├── boards/                # 各开发板适配层
│   ├── assets.*               # 资源包管理与下载/应用
│   ├── mcp_server.*           # 设备侧 MCP 服务
│   ├── ota.*                  # 固件升级与版本检查
│   └── settings.*             # 设备配置持久化
├── docs/                      # 协议与 MCP 相关文档
├── partitions/                # 分区表
├── scripts/                   # 资源转换、打包、发布、调试脚本
├── managed_components/        # 组件缓存/托管依赖
├── sdkconfig*                 # IDF 配置
└── CMakeLists.txt             # 工程入口
```

## 核心模块说明

### 1. 应用入口

- [main/main.cc](main/main.cc)：初始化事件循环与 NVS，随后启动 `Application`
- [main/application.cc](main/application.cc)：项目核心调度中心，负责
  - 设备状态切换
  - 协议选择与连接
  - 音频回调处理
  - OTA 检查
  - 资源包检查
  - MCP 消息发送

### 2. 音频系统

- [main/audio/](main/audio)
- 包含音频服务、音频编解码器适配、唤醒词实现和调试能力
- 支持不同 codec 芯片与不同板型音频链路

### 3. 显示系统

- [main/display/](main/display)
- 同时支持 OLED、LCD 和基于 LVGL 的 UI 渲染
- 支持 emoji、图片和状态文本显示

### 4. 通信协议

- [main/protocols/websocket_protocol.cc](main/protocols/websocket_protocol.cc)
- [main/protocols/mqtt_protocol.cc](main/protocols/mqtt_protocol.cc)
- 设备会根据配置选择协议，并统一通过 `Protocol` 抽象与上层交互

### 5. 板级适配

- [main/boards/](main/boards)
- 每个板型目录通常包含：
  - `*_board.cc`：板级初始化
  - `config.h`：引脚和硬件参数
  - `config.json`：构建目标与附加 `sdkconfig`
  - `README.md`：板型说明

## 如何编译

### 环境要求

- `ESP-IDF 5.4` 或以上
- 建议使用 Linux 或 macOS
- 建议通过 VS Code / Cursor 的 ESP-IDF 插件管理环境

### 基本命令

```bash
idf.py set-target esp32s3
idf.py menuconfig
idf.py build
idf.py flash monitor
```

### 选择板型

在 `menuconfig` 中进入：

```text
Xiaozhi Assistant -> Board Type
```

然后选择目标开发板。

如果你是为某个板型做批量发布，建议直接查看对应目录下的 `config.json`，并使用仓库脚本构建。

参考文档见 [main/boards/README.md](main/boards/README.md)。

## 当前仓库里值得优先看的文档

- [docs/mcp-usage.md](docs/mcp-usage.md)：MCP 控制用法
- [docs/mcp-protocol.md](docs/mcp-protocol.md)：设备侧 MCP 协议流程
- [docs/websocket.md](docs/websocket.md)：WebSocket 协议
- [docs/mqtt-udp.md](docs/mqtt-udp.md)：MQTT + UDP 协议
- [main/audio/README.md](main/audio/README.md)：音频相关说明

## 脚本与辅助工具

仓库内有不少配套脚本，主要分为四类：

- 资源构建
  - `scripts/spiffs_assets/`
  - `scripts/build_default_assets.py`
  - `scripts/gen_lang.py`
- 音频处理
  - `scripts/ogg_converter/`
  - `scripts/p3_tools/`
  - `scripts/mp3_to_ogg.sh`
- 图片转换
  - `scripts/Image_Converter/`
- 调试与发布
  - `scripts/audio_debug_server.py`
  - `scripts/release.py`
  - `scripts/versions.py`

如果你要做自定义语音包、图片资源或板型发布，这部分值得先看。

## 适合怎样的二次开发

- 新增自定义开发板
- 替换音频 codec、屏幕或按键方案
- 接入不同的服务端协议或私有服务端
- 扩展设备端 MCP 工具
- 做本地 UI、表情、语音资源定制
- 增加 OTA、激活或资产分发逻辑

## 开发注意事项

- 板型不要直接覆盖已有配置；新增板型时应保持唯一标识，避免后续 OTA 串板
- `sdkconfig` 只是当前工作区的一个构建快照，不代表仓库唯一推荐配置
- 仓库中包含 `build/` 目录和若干构建产物，阅读时注意区分源码与生成文件
- 如果你要为特定硬件发布固件，优先以板型目录下的 `config.json` 和 `README.md` 为准

## 许可证

本项目使用 [LICENSE](LICENSE) 中声明的 MIT 许可证。
