# Web-Scrcpy 项目健壮化与架构升级规划

## 一、现状分析

### 当前项目结构
```
web-scrcpy/
├── app.py              — Flask/SocketIO 主服务（131 行），全局状态 + 路由 + 事件处理混在一起
├── config.py           — 硬编码配置，无环境变量覆盖，SECRET_KEY 明文
├── scrcpy/
│   ├── __init__.py     — Scrcpy 类（218 行），socket 管理 + 线程管理 + 数据收发
│   └── scrcpy-server   — 二进制文件
├── adb/                — ADB 封装（已拆分，结构良好）
├── templates/
│   └── index.html      — 单文件前端（327 行），HTML + CSS + JS 全部内联
├── static/js/          — 前端 JS 文件（input.js, video_parser.js 等）
└── requirements.txt    — 未锁定版本
```

### 核心问题
1. **后端全局状态泛滥**：`scpy_ctx`、`client_sid`、`message_queue` 等用全局变量管理，难以扩展为多客户端
2. **单文件 app.py 职责过重**：路由、SocketIO 事件、视频转发、日志初始化、CLI 参数全在一个文件
3. **配置管理薄弱**：SECRET_KEY 明文、无环境变量覆盖、未使用配置项（MAX_FPS/STAY_AWAKE/SHOW_TOUCHES）
4. **前端无模块化**：327 行 HTML 内联大量 JS，input.js 单文件 494 行
5. **无测试/无 CI/无 lint**：纯原型状态，无法保证后续功能的质量
6. **错误处理不统一**：部分用异常、部分用返回值、部分静默忽略
7. **scrcpy_start 中 time.sleep(1) 硬编码等待**：不可靠
8. **video_parser.js 缓冲区 O(n²) 拷贝**：性能瓶颈

---

## 二、目标架构

### 重构后的项目结构
```
web-scrcpy/
├── app.py                    — 入口（仅 CLI 解析 + 启动服务器，约 30 行）
├── config.py                 — 配置管理（支持环境变量覆盖）
├── server/
│   ├── __init__.py
│   ├── app_factory.py        — Flask 应用工厂（创建 app + socketio）
│   ├── routes.py             — HTTP 路由
│   ├── socket_handlers.py    — SocketIO 事件处理器
│   ├── session.py            — 客户端会话管理（替代全局变量）
│   └── video_relay.py        — 视频数据中继（队列 + 发送线程）
├── scrcpy/
│   ├── __init__.py
│   ├── connection.py         — Socket 连接管理（创建/关闭/重试）
│   ├── receiver.py           — 数据接收线程（video/audio/control）
│   ├── control.py            — 控制数据发送
│   ├── protocol.py           — scrcpy 协议常量与二进制编解码
│   └── scrcpy-server
├── adb/                      — 保持不变（结构已良好）
├── templates/
│   └── index.html            — 精简 HTML 骨架
├── static/
│   ├── js/
│   │   ├── app.js            — 前端主入口（SocketIO 连接 + 初始化）
│   │   ├── input.js          — 输入处理（ScrcpyInput 类）
│   │   ├── video-parser.js   — 视频流解析（VideoParser 类）
│   │   ├── stats.js          — 统计面板逻辑
│   │   ├── jmuxer.min.js     — 第三方库
│   │   └── ...
│   └── css/
│       └── main.css          — 从 HTML 中提取的样式
├── tests/
│   ├── test_config.py
│   ├── test_session.py
│   ├── test_video_relay.py
│   └── test_protocol.py
├── .gitignore
├── requirements.txt          — 锁定版本
└── AGENTS.md
```

---

## 三、分阶段实施计划

### 阶段 1：后端核心拆分（优先级最高）

> 目标：消除全局状态，拆分 app.py 为模块化结构，为后续功能扩展打好基础

#### 1.1 创建 `server/session.py` — 客户端会话管理
- 用 `ClientSession` 类封装当前全局变量（`scpy_ctx`、`client_sid`、`message_queue`）
- 提供 `connect(sid)` / `disconnect()` / `is_active` 等方法
- 后续扩展多客户端时只需修改此类

#### 1.2 创建 `server/video_relay.py` — 视频数据中继
- 从 app.py 提取 `video_send_task()` 和 `send_video_data()`
- 封装为 `VideoRelay` 类，持有 `message_queue` 和发送线程
- 提供 `start(sid)` / `stop()` / `feed(data)` 方法
- 退出时自动清空队列

#### 1.3 创建 `server/socket_handlers.py` — SocketIO 事件处理
- 从 app.py 提取 `handle_connect` / `handle_disconnect` / `handle_control_data`
- 通过 `ClientSession` 实例操作状态，不再使用 global
- 注册到 socketio 实例

#### 1.4 创建 `server/app_factory.py` — 应用工厂
- `create_app()` 函数：创建 Flask app + SocketIO 实例
- 注册路由、SocketIO 事件处理器
- 初始化日志

#### 1.5 精简 `app.py` 为入口文件
- 仅保留 CLI 参数解析 + `create_app()` + `socketio.run()`
- 约 30 行

#### 1.6 重构 `config.py`
- SECRET_KEY 从环境变量读取，回退到随机生成
- 所有配置项支持环境变量覆盖（`os.environ.get('WEB_SCRCPY_PORT', default)`）
- VIDEO_BIT_RATE 改为 int 类型
- 删除未使用的配置项或将其应用到 scrcpy 启动命令

---

### 阶段 2：Scrcpy 模块拆分与健壮化

> 目标：拆分大文件、消除硬编码等待、统一错误处理

#### 2.1 创建 `scrcpy/connection.py` — 连接管理
- 提取 socket 创建/连接/关闭逻辑
- 用重试连接替代 `time.sleep(1)` 硬编码等待
- 连接超时可配置

#### 2.2 创建 `scrcpy/receiver.py` — 数据接收
- 提取 `receive_video_data` / `receive_audio_data` / `handle_control_conn`
- 统一接收循环模式（模板方法）
- 添加 socket 超时设置，防止 `recv` 永久阻塞

#### 2.3 创建 `scrcpy/control.py` — 控制数据发送
- 提取 `scrcpy_send_control`
- 添加发送队列，避免直接写 socket 阻塞

#### 2.4 创建 `scrcpy/protocol.py` — 协议常量
- 集中定义 scrcpy 协议的消息类型（TYPE_KEY=0, TYPE_TOUCH=2 等）
- 后续前端 input.js 的协议编解码逻辑与此对应

#### 2.5 统一错误处理
- Scrcpy 启动失败时抛出明确异常（而非 return）
- app 层捕获异常并通知前端（SocketIO error 事件）
- 添加 `scrcpy_start` 返回状态，让调用方知道是否成功

---

### 阶段 3：前端模块化

> 目标：拆分 327 行 index.html，JS 模块化，提升可维护性

#### 3.1 提取 CSS 到独立文件
- 从 `index.html` 的 `<style>` 提取到 `static/css/main.css`

#### 3.2 提取内联 JS 到独立模块
- `static/js/app.js` — SocketIO 连接管理 + JMuxer 初始化 + 事件绑定
- `static/js/stats.js` — 统计面板逻辑（`statsTracker` 对象）
- `index.html` 仅保留 HTML 骨架 + `<script src>` 引用

#### 3.3 修复 `s` 键冲突
- 统计面板快捷键改为 `Ctrl+Shift+S`，避免与输入法/文本输入冲突

#### 3.4 优化 `video_parser.js` 缓冲区
- 用分块存储替代每次 `new Uint8Array` 全量拷贝
- 添加最大缓冲区限制，防止内存暴涨

#### 3.5 修复 `video_parser.js` DataView offset 问题
- `scrcpyProcessBuffer` 中 `new DataView(this.buffer.buffer)` 改为基于 `this.buffer` 的正确偏移

---

### 阶段 4：质量保障基础设施

> 目标：建立测试、lint、CI 基础，保证后续开发质量

#### 4.1 添加 pytest 测试框架
- `tests/test_config.py` — 配置加载、环境变量覆盖
- `tests/test_session.py` — 客户端会话管理
- `tests/test_video_relay.py` — 视频中继队列
- `tests/test_protocol.py` — scrcpy 协议编解码

#### 4.2 添加代码质量工具
- 添加 `ruff` 作为 linter + formatter（替代 flake8 + black，更快更现代）
- 添加 `pre-commit` 配置
- requirements.txt 锁定版本（或迁移到 pyproject.toml）

#### 4.3 完善 `.gitignore`
- 添加 `*.pyc`、`.env`、`venv/`、`__pycache__/`、`*.egg-info/` 等

#### 4.4 迁移到 `pyproject.toml`
- 项目元数据、依赖、工具配置统一到 pyproject.toml
- 保留 requirements.txt 作为兼容

---

### 阶段 5：安全加固

> 目标：基本安全防护，防止未授权访问

#### 5.1 添加密码认证
- config.py 新增 `AUTH_PASSWORD` 配置项
- 前端连接时需提供密码（URL 参数或登录表单）
- SocketIO `connect` 事件验证密码

#### 5.2 SECRET_KEY 安全化
- 从环境变量 `WEB_SCRCPY_SECRET_KEY` 读取
- 未设置时生成随机值并打印到日志

#### 5.3 HTTPS 支持
- 添加 `--ssl-cert` / `--ssl-key` CLI 参数
- 开发模式可用自签名证书

---

### 阶段 6：为未来功能预留扩展点

> 目标：在架构层面为常见功能需求预留接口

#### 6.1 多客户端支持（会话管理已就绪）
- 阶段 1 的 `ClientSession` 可扩展为会话池
- 添加 `SessionManager` 管理多个 `ClientSession`
- 视频流可选择性共享或独占

#### 6.2 设备管理扩展
- `adb/device.py` 扩展为支持多设备
- 添加设备选择 API（前端下拉选择）

#### 6.3 录屏功能
- `VideoRelay.feed()` 时同时写入文件
- 添加 `--record` CLI 参数

#### 6.4 剪贴板同步
- 完善 input.js 中未完成的剪贴板读取逻辑
- 后端添加 `set_clipboard` / `get_clipboard` 控制消息

---

## 四、实施优先级与依赖关系

```
阶段 1（后端核心拆分）
  ├─ 1.6 config.py 重构 ────────── 无依赖，可先做
  ├─ 1.1 session.py ────────────── 无依赖
  ├─ 1.2 video_relay.py ────────── 依赖 1.1
  ├─ 1.3 socket_handlers.py ────── 依赖 1.1, 1.2
  ├─ 1.4 app_factory.py ────────── 依赖 1.1-1.3
  └─ 1.5 精简 app.py ──────────── 依赖 1.4

阶段 2（Scrcpy 模块拆分）────────── 依赖阶段 1
  ├─ 2.4 protocol.py ──────────── 无依赖，可先做
  ├─ 2.1 connection.py
  ├─ 2.2 receiver.py
  ├─ 2.3 control.py
  └─ 2.5 统一错误处理

阶段 3（前端模块化）─────────────── 与阶段 2 可并行
  ├─ 3.1 提取 CSS
  ├─ 3.2 提取 JS 模块
  ├─ 3.3 修复 s 键冲突
  ├─ 3.4 优化缓冲区
  └─ 3.5 修复 DataView offset

阶段 4（质量保障）───────────────── 依赖阶段 1-2
  ├─ 4.4 pyproject.toml ───────── 可先做
  ├─ 4.3 .gitignore ──────────── 可先做
  ├─ 4.2 ruff + pre-commit
  └─ 4.1 pytest 测试

阶段 5（安全加固）───────────────── 依赖阶段 1
  ├─ 5.2 SECRET_KEY ──────────── 可在 1.6 中一起做
  ├─ 5.1 密码认证
  └─ 5.3 HTTPS 支持

阶段 6（扩展预留）───────────────── 依赖阶段 1-5
```

---

## 五、关键设计决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 应用工厂模式 | `create_app()` | 便于测试时创建不同配置的 app 实例 |
| 会话管理 | 单例 `ClientSession` | 保持当前单客户端限制，但封装为类便于后续扩展 |
| 配置覆盖 | 环境变量优先 | 12-Factor App 原则，Docker 友好 |
| 前端模块化 | ES6 class 独立文件 | 无需构建工具，保持项目简洁 |
| Linter | ruff | 比 flake8+black 更快，单工具替代多工具 |
| 测试框架 | pytest | Python 社区标准，简洁强大 |
| 连接重试 | 指数退避重试 | 替代 time.sleep(1)，更可靠 |

---

## 六、风险与注意事项

1. **向后兼容**：CLI 参数和 config.py 的默认值应保持不变，新功能通过新参数/环境变量启用
2. **渐进式重构**：每个阶段完成后项目应可正常运行，避免大爆炸式重写
3. **前端无构建工具**：保持纯 JS 文件，不引入 webpack/vite，降低复杂度
4. **scrcpy 协议兼容**：protocol.py 仅做常量集中管理，不改变协议格式
5. **adb/ 包保持不变**：结构已良好，无需重构
