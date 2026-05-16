import os

# Flask 服务器配置
HOST = "0.0.0.0"
PORT = 5800
SECRET_KEY = "secret!"

VIDEO_CODEC = "h264"
# 视频码率（bps，默认 1Mbps）
VIDEO_BIT_RATE = "256000"

# scrcpy-server jar 文件路径
SCRCPY_SERVER_PATH = os.path.join(os.path.dirname(__file__), "scrcpy", "scrcpy-server")

# 设备端 jar 目标路径
DEVICE_SERVER_PATH = "/data/local/tmp/scrcpy-server.jar"

# ADB forward 本地端口
LOCAL_PORT = 5555

# 最大帧率（0 表示不限制）
MAX_FPS = 0

# 保持设备唤醒（防止屏幕熄灭）
STAY_AWAKE = False

# 显示触摸点（用于演示/录屏）
SHOW_TOUCHES = False

# 是否启用音频转发
ENABLE_AUDIO = False

# Socket 接收缓冲区大小
VIDEO_RECV_SIZE = 20480
AUDIO_RECV_SIZE = 1024
CONTROL_RECV_SIZE = 1024

# 日志配置
# 日志级别: DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_LEVEL = "INFO"
# 日志格式
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
# 日志文件路径（为空则只输出到控制台）
LOG_FILE = os.path.join(os.path.dirname(__file__), "logs", "web-scrcpy.log")
# 日志文件最大大小（字节），超过后自动轮转
LOG_MAX_BYTES = 1024 * 1024 * 5  # 5MB
# 保留的日志文件数量
LOG_BACKUP_COUNT = 5
