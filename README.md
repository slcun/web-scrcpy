# Web-Scrcpy

通过浏览器远程控制 Android 手机。后端 Flask + Flask-SocketIO，前端 JMuxer v3+ MSE 播放 H.264/H.265 视频流。

## 效果展示

![效果展示](./animation.gif)

## 功能特性

- 🖱️ 鼠标点击/拖拽/滚轮映射为触摸操作
- ⌨️ 键盘按键映射为 Android 按键
- 📱 触屏设备直接触摸操作
- 🎬 H.264 / H.265 双编码支持（默认 H.265，降低带宽）
- 📊 实时统计面板（码率/帧率/分辨率/编码，`Ctrl+S` 切换）
- 🔌 快捷按钮（电源/音量/返回/主页/菜单）
- 📝 日志轮转（5MB 轮转，保留 5 份）

## 前置条件

- `adb` 在 PATH 中，或 `adb/adb.exe` / `scrcpy/adb.exe` 存在于项目内（自动查找）
- Android 设备已连接 + 开启 USB 调试
- `scrcpy/scrcpy-server` 文件存在（需自行获取编译好的 jar）
- Python 3.13+
- 同一时间只允许一个客户端连接

## 快速开始

```bash
# 克隆项目
git clone https://github.com/baixin1228/web-scrcpy.git
cd web-scrcpy

# 安装依赖
pip install -r requirements.txt

# 启动（默认 H.265, 256Kbps, 15fps, 端口 5800）
python app.py

# 自定义参数
python app.py --video_bit_rate 4096000            # 覆盖码率
python app.py --video_codec h264                  # 切回 H.264
python app.py --video_bit_rate 1024000 --video_codec h265
```

浏览器访问 `http://localhost:5800` 即可。

## 项目结构

```
web-scrcpy/
├── app.py                  — 入口（CLI 解析 + 启动服务器）
├── config.py               — 集中配置项（端口/码率/编码/日志等）
├── server/                 — 后端服务模块
│   ├── __init__.py         — 应用工厂（create_app）+ 日志初始化
│   ├── session.py          — 客户端会话管理（替代全局变量）
│   ├── video_relay.py      — 视频数据中继（队列 → SocketIO）
│   └── handlers.py         — SocketIO 事件处理器
├── scrcpy/                 — Scrcpy 协议层
│   ├── __init__.py         — Scrcpy 类（服务编排）
│   ├── connection.py       — Socket 连接管理（创建/关闭/重试）
│   ├── receiver.py         — 数据接收线程（video/audio/control）
│   ├── control.py          — 控制数据发送
│   ├── protocol.py         — 协议常量
│   └── scrcpy-server       — 设备端 jar（需自行获取）
├── adb/                    — ADB 封装
│   ├── client.py           — AdbClient 门面
│   ├── device.py           — 设备检测
│   ├── push.py             — 文件推送
│   ├── forward.py          — 端口转发
│   ├── shell.py            — Shell 命令
│   ├── utils.py            — 工具函数
│   └── errors.py           — 自定义异常
├── templates/
│   └── index.html          — 前端页面骨架
├── static/
│   ├── css/main.css        — 样式
│   └── js/
│       ├── app.js          — 前端主入口（SocketIO + JMuxer 编排）
│       ├── input.js        — 输入处理（鼠标/键盘/触摸）
│       ├── video_parser.js — 视频流 NALU 解析
│       ├── stats.js        — 统计面板
│       ├── jmuxer.min.js   — JMuxer v3+（MSE 封装）
│       └── ...
└── requirements.txt
```

### 数据流

**视频**: 设备 → ADB forward → `video_socket` → `message_queue` → `VideoRelay` → SocketIO `video_data` → `VideoParser` 解析 NALU → `JMuxer.feed()` → MSE → `<video>`

**控制**: 鼠标/触摸 → `input.js` 构造二进制 → SocketIO `control_data` → `control_socket.send()` → ADB forward → 设备

## 配置项

编辑 `config.py` 或通过命令行参数覆盖：

| 配置项 | 默认值 | 命令行参数 | 说明 |
|--------|--------|------------|------|
| `PORT` | `5800` | — | 监听端口 |
| `VIDEO_CODEC` | `"h265"` | `--video_codec` | `"h264"` 切回 H.264 |
| `VIDEO_BIT_RATE` | `"256000"` | `--video_bit_rate` | 码率 bps |
| `MAX_FPS` | `15` | — | 最大帧率，`0`=不限制 |
| `ENABLE_AUDIO` | `False` | — | 音频（目前仅计数不转发） |
| `VIDEO_RECV_SIZE` | `20480` | — | video socket 接收缓冲区 |
| `LOG_LEVEL` | `"INFO"` | — | 日志级别 |

## 编解码说明

- **H.264**（`--video_codec h264`）：兼容性最好，所有现代浏览器均支持
- **H.265**（默认）：带宽更低，需浏览器支持 `video/mp4; codecs="hev1.*"` 的 MSE（Chrome 105+、Edge、Safari）

## 参与贡献

1. Fork 本项目
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m "Add some feature"`
4. 推送分支：`git push origin feature/your-feature`
5. 提交 Pull Request

## 开源协议

[Apache License 2.0](./LICENSE.txt)