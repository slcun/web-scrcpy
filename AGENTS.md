# web-scrcpy

通过浏览器远程控制 Android 手机。后端 Flask + Flask-SocketIO，前端 JMuxer v3+ MSE 播放 H.264/H.265。

## 启动

```bash
pip install -r requirements.txt
python app.py                                     # 默认 0.0.0.0:5800, H.265, 256Kbps, 15fps
python app.py --video_bit_rate 4096000            # 覆盖码率
python app.py --video_codec h264                  # 切回 H.264
python app.py --video_bit_rate 1024000 --video_codec h265
```

config.py 的默认值均可被命令行覆盖。

## 开发与运维

### 环境准备
```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 检查 adb 是否可用
adb devices

# 获取 scrcpy-server（需手动下载）
# 从官方仓库 https://github.com/Genymobile/scrcpy/releases 下载最新版 scrcpy-server
# 放置到 scrcpy/scrcpy-server（可执行权限）
wget https://github.com/Genymobile/scrcpy/releases/download/v2.4/scrcpy-server-v2.4
mv scrcpy-server-v2.4 scrcpy/scrcpy-server
chmod +x scrcpy/scrcpy-server
```

### 运行服务
```bash
# 默认启动（H.265, 256Kbps, 15fps）
python app.py

# 指定码率和编码
python app.py --video_bit_rate 4096000 --video_codec h264

# 调试模式（启用更详细日志）
export LOG_LEVEL=DEBUG
python app.py
```

### 设备连接检查
```bash
# 查看已连接设备
adb devices

# 若设备未列出，检查 USB 调试是否开启
adb kill-server
adb start-server
```

### 日志查看
```bash
# 实时查看日志输出
tail -f logs/web-scrcpy.log

# 清空日志文件（5MB 轮转，保留5份）
> logs/web-scrcpy.log
```

## 前置条件

- `adb` 在 PATH 中，或 `adb/adb.exe` / `scrcpy/adb.exe` 存在于项目内（自动查找）
- Android 设备已连接 + 开启 USB 调试
- `scrcpy/scrcpy-server` 文件存在（需自行获取，编译好的 jar）
- 同一时间只允许一个客户端（全局 `server.session`）

## 架构

```
app.py                    — 入口（5 行）：CLI 解析 → create_app() → socketio.run()

server/                   — Flask/SocketIO 服务层
  ├─ __init__.py           create_app() 工厂 + setup_logging()
  ├─ session.py            ClientSession：封装全局状态（sid/scrcpy/queue）
  ├─ video_relay.py        VideoRelay：队列 → SocketIO 发送线程
  └─ handlers.py           SocketIO 事件：connect/disconnect/control_data

scrcpy/                   — Scrcpy 核心
  ├─ __init__.py           Scrcpy 类：启动/停止编排
  ├─ connection.py         Socket 创建 + 重试连接
  ├─ receiver.py           视频/音频/控制接收循环
  ├─ control.py            控制数据发送
  └─ protocol.py           scrcpy 协议常量

adb/                      — ADB 封装包（client.py 门面 + 子模块）
device/                   — 设备管理服务层（框架就绪，功能逐步添加）

templates/index.html      — 精简 HTML 骨架
static/
  ├─ css/main.css         从 HTML 提取的样式
  └─ js/
      ├─ app.js           主入口：SocketIO + JMuxer + VideoParser 编排
      ├─ stats.js          统计面板（码率/帧率/分辨率/编码）
      ├─ input.js          触摸/鼠标/键盘 → scrcpy 协议二进制
      ├─ video_parser.js   NALU 解析（H.264/H.265）
      └─ lib/              第三方库
```

### 模块职责详解

**server/ 服务层**
- `__init__.py` – 应用工厂，初始化日志、创建 Flask/SocketIO 实例
- `session.py` – `ClientSession` 类管理单个客户端会话状态（sid、scrcpy 实例、消息队列）
- `video_relay.py` – `VideoRelay` 类从队列读取视频数据并通过 SocketIO 发送给客户端
- `handlers.py` – SocketIO 事件处理器：`connect`/`disconnect`/`control_data`/`screenshot`

**scrcpy/ 协议层**
- `__init__.py` – `Scrcpy` 类负责启动/停止 scrcpy 服务，管理三个 socket 连接和接收线程
- `connection.py` – 提供 `connect_with_retry`（指数退避重试）和 `close_socket` 工具
- `receiver.py` – 三个接收线程：`receive_video`、`receive_audio`、`receive_control`
- `control.py` – `send_control` 函数将控制数据发送到 control socket
- `protocol.py` – scrcpy 协议常量（如消息类型、键码）

**adb/ 封装层**
- `client.py` – `AdbClient` 门面类，提供 `check_device`、`push_server`、`setup_forward`、`start_server` 等方法
- 各子模块（`device.py`、`forward.py`、`shell.py` 等）实现具体 ADB 操作

**前端 JavaScript**
- `app.js` – 主入口，初始化 SocketIO、JMuxer、VideoParser，协调各模块
- `video_parser.js` – 解析 H.264/H.265 NALU，处理 emulation prevention bytes
- `input.js` – 将鼠标/键盘/触摸事件转换为 scrcpy 控制协议二进制
- `stats.js` – 实时统计面板（码率、帧率、分辨率、编码）

### 数据流

**视频**: 设备 → ADB forward → `video_socket` → `message_queue` → `VideoRelay` → SocketIO `video_data` → `VideoParser` → `jmuxer.feed()` → MSE SourceBuffer → `<video>`

**控制**: 鼠标/触摸 → `input.js` 构造二进制 → SocketIO `control_data` → `Scrcpy.scrcpy_send_control()` → `control_socket.send()` → ADB forward → 设备

## 关键实现细节

- **默认 H.265**（config.py `VIDEO_CODEC = "h265"`），H.264 仍支持。
- **H.265 SPS 解析需要去 emulation prevention byte**：`VideoParser.removeEmulationPrevention()` 在 `parseH265SPS` 前调用，否则 ExpGolomb 解析错位得负数分辨率。
- **scrcpy 帧可能含多个 NALU**（VPS+SPS+PPS 合在一帧里不到 100 字节），`video_parser.js` 的 `processBufferH265` 用 `findSequence(...)` 递归拆分。
- **统计面板**：右上角显示码率/帧率/分辨率/编码，按 `Ctrl+Shift+S` 切换显示/隐藏。
- **日志系统**：`RotatingFileHandler`，输出到 `logs/web-scrcpy.log`（5MB 轮转，保留 5 份）。
- **连接重试**：`scrcpy/connection.py` 用指数退避重试连接，替代硬编码 `time.sleep(1)`。
- **单客户端限制**：`server/__init__.py` 中的全局 `session` 变量确保同一时间只有一个活跃连接，新连接会被拒绝（`handlers.py` 的 `handle_connect` 检查 `session.is_active`）。
- **视频数据流缓冲**：`ClientSession.message_queue` 作为视频数据缓冲区，`VideoRelay.run()` 以 10ms 超时从队列读取并发送，避免阻塞。
- **连接重试机制**：`scrcpy/connection.py` 的 `connect_with_retry` 使用指数退避（1s, 2s, 4s, 8s）重试连接，避免因设备未就绪导致启动失败。
- **H.265 SPS 解析陷阱**：`video_parser.js` 的 `parseH265SPS` 前必须调用 `removeEmulationPrevention()`，否则 ExpGolomb 解析会错位得到负数分辨率。

## 代码约定

- 注释用中文
- 函数加注释说明目的
- 无测试 / 无 linter / 无 formatter
- 依赖：仅 `flask` + `flask-socketio`

## 常用 config.py 修改项

| 项 | 默认值 | 说明 |
|----|--------|------|
| `PORT` | `5800` | 监听端口 |
| `VIDEO_CODEC` | `"h265"` | `"h264"` 切回 H.264 |
| `VIDEO_BIT_RATE` | `"256000"` | 码率 bps |
| `MAX_FPS` | `15` | 最大帧率，`0`=不限制 |
| `VIDEO_RECV_SIZE` | `20480` | video socket recv buf |
| `ENABLE_AUDIO` | `False` | 音频目前只计数不转发 |

### 配置覆盖方式

1. **命令行参数**（仅限码率和编码）：
   ```bash
   python app.py --video_bit_rate 1024000 --video_codec h264
   ```

2. **直接修改 config.py**：
   修改 `config.py` 中的常量（如 `PORT`、`MAX_FPS`、`ENABLE_AUDIO` 等），重启生效。

3. **环境变量**（暂不支持，但可扩展）：
   当前版本未使用环境变量，如需可修改 `config.py` 增加 `os.getenv()` 读取。

## 故障排除

### 连接问题
- **"设备检测失败"**：检查 USB 调试是否开启，`adb devices` 是否列出设备。
- **"建立连接失败"**：确认 `scrcpy-server` 文件存在且具有可执行权限，设备端 Java 环境正常。

### 视频无法播放
- **黑屏/绿屏**：检查浏览器是否支持 H.265（Chrome 105+、Edge、Safari），可切换为 H.264 测试。
- **分辨率异常**：确认 `video_parser.js` 正确移除 emulation prevention bytes（仅 H.265 需要）。

### 控制无响应
- **触摸/按键无效**：检查 `input.js` 是否正确构造二进制协议，可通过浏览器开发者工具查看 `control_data` 事件是否发出。

### 日志排查
- 日志文件位于 `logs/web-scrcpy.log`，设置 `LOG_LEVEL=DEBUG` 可获取更详细信息。
- 若日志文件未生成，检查 `logs` 目录权限及磁盘空间。