import os

# Flask 服务器配置
HOST = "0.0.0.0"
PORT = 5800
SECRET_KEY = "secret!"

VIDEO_CODEC = "h264"
# 视频码率（bps，默认 1Mbps）
VIDEO_BIT_RATE = "512000"

# ADB 可执行文件路径（空字符串则用 PATH 中的 adb）
_ADB_IN_SCRCPY = os.path.join(os.path.dirname(__file__), "scrcpy", "adb.exe")
ADB_PATH = _ADB_IN_SCRCPY if os.path.exists(_ADB_IN_SCRCPY) else "adb"

# scrcpy-server jar 文件路径
SCRCPY_SERVER_PATH = os.path.join(os.path.dirname(__file__), "scrcpy", "scrcpy-server")

# 设备端 jar 目标路径
DEVICE_SERVER_PATH = "/data/local/tmp/scrcpy-server.jar"

# ADB forward 本地端口
LOCAL_PORT = 5555

# Socket 接收缓冲区大小
VIDEO_RECV_SIZE = 20480
AUDIO_RECV_SIZE = 1024
CONTROL_RECV_SIZE = 1024
