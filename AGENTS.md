# web-scrcpy

通过浏览器远程控制 Android 手机。后端 Flask + Flask-SocketIO，前端 jmuxer.js 播放 H.264 流。

## 启动

```bash
pip install -r requirements.txt
python app.py                     # 默认 0.0.0.0:5000
python app.py --video_bit_rate 4096000  # 自定义码率（覆盖 config.py）
```

编辑 `config.py` 可修改端口、secret key、adb 路径、缓冲区大小等参数。

## 前置条件

- `adb` 在 PATH 中，Android 设备已连接且开启 USB 调试
- `scrcpy/scrcpy-server` 文件（ADB push 到设备用）
- 同一时间只允许一个客户端连接（全局 `scpy_ctx` 限制）

## 架构

```
app.py            — Flask/SocketIO 主服务，单文件入口
scrcpy/           — Scrcpy 包：__init__.py（Scrcpy 类）+ scrcpy-server jar
templates/index.html — 前端页面，含 video 标签 + jmuxer
static/js/        — socket.io.js, input.js, h264-sps-parser.js, video_parser.js, jmuxer.min.js
```

- Video socket 接收裸 H.264 → `message_queue` → SocketIO `video_data` 事件 → 前端 `video_parser.js` 解析 NALU → jmuxer 喂给 MSE
- Control socket 接收 `control_data` 事件二进制数据 → 直接 `socket.send()` 到 scrcpy-server
- 音视频 + control 各一条独立 TCP 连接，均通过 ADB forward (tcp:5555 → localabstract:scrcpy)

## 代码约定

- 注释用中文
- 函数加注释说明目的
- 无测试 / 无 linter / 无 formatter / 无 CI（纯原型项目）
- 依赖仅 `flask` + `flask-socketio`

## 文件说明

| 文件 | 作用 |
|------|------|
| `config.py` | 集中配置项：端口、码率、adb 路径、缓冲区大小等 |
| `app.py` | Flask 路由 + SocketIO 事件处理 + 参数解析，约 70 行 |
| `scrcpy/__init__.py` | scrcpy server 管理：push、forward、启动、3 路 socket 收发 |
| `scrcpy/scrcpy-server` | 编译好的 scrcpy server jar（需自行获取，非源码） |
| `requirements.txt` | 仅 `flask`、`flask-socketio` |
