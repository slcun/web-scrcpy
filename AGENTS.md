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

## 前置条件

- `adb` 在 PATH 中，或 `adb/adb.exe` / `scrcpy/adb.exe` 存在于项目内（自动查找）
- Android 设备已连接 + 开启 USB 调试
- `scrcpy/scrcpy-server` 文件存在（需自行获取，编译好的 jar）
- 同一时间只允许一个客户端（全局 `scpy_ctx`）

## 架构

```
app.py              — Flask/SocketIO 主服务（121 行）
   ├─ video_send_task()   从 message_queue 读 → SocketIO video_data
   ├─ send_video_data()   往 message_queue 写（由 Scrcpy 回调）
   └─ handle_control_data()  控制数据直通 scrcpy-server

adb/                — ADB 封装包（client.py 门面 + device/push/forward/shell/utils）
scrcpy/__init__.py  — Scrcpy 类：3 路 TCP socket（video/audio/control），均 TCP_NODELAY
templates/index.html — 前端（328 行）：VideoParser 解析 NALU → JMuxer 喂给 MSE
static/js/          — video_parser.js(input.js(按键映射/触摸) jmuxer.min.js(v3+) socket.io.js
```

### 数据流

**视频**: 设备 → ADB forward → `video_socket` → `message_queue` → `video_send_task` → SocketIO `video_data` → WebSocket → `VideoParser.appendData()` → fetch NALU → `jmuxer.feed()` → MSE SourceBuffer → `<video>`

**控制**: 鼠标/触摸 → `input.js` 构造二进制 → SocketIO `control_data` → `control_socket.send()` → ADB forward → 设备

**瓶颈**: `message_queue` 引入一次额外线程切换。前端每帧 `new Uint8Array(data)` + `set()` 做一次内存拷贝。

## 关键实现细节

- **默认 H.265**（config.py `VIDEO_CODEC = "h265"`），H.264 仍支持。
- **H.265 SPS 解析需要去 emulation prevention byte**：`VideoParser.removeEmulationPrevention()` 在 `parseH265SPS` 前调用，否则 ExpGolomb 解析错位得负数分辨率。
- **scrcpy 帧可能含多个 NALU**（VPS+SPS+PPS 合在一帧里不到 100 字节），`video_parser.js` 的 `processBufferH265` 用 `findSequence(...)` 递归拆分。
- **统计面板**：右上角显示码率/帧率/分辨率/编码，按 `s` 键切换显示/隐藏。
- **日志系统**：`RotatingFileHandler`，输出到 `logs/web-scrcpy.log`（5MB 轮转，保留 5 份）。

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
