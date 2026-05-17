"""Shell 执行：adb shell 操作"""

import subprocess
import config
from .utils import _popen_adb, _run_adb, logger


def start_server_process(video_bit_rate, video_codec):
    """
    在设备上启动 scrcpy-server 进程。
    返回 subprocess.Popen 对象，调用方负责读取 stderr 和管理进程生命周期。
    """
    logger.info(f"启动 scrcpy 服务器 (编码: {video_codec})...")
    logger.info(f"video_codec 参数值: {video_codec}")
    cmd = [
        "shell",
        f"CLASSPATH={config.DEVICE_SERVER_PATH}",
        "app_process",
        "/",
        "com.genymobile.scrcpy.Server",
        "3.1",
        "tunnel_forward=true",
        "log_level=VERBOSE",
        f"video_codec={video_codec}",
        f"video_bit_rate={video_bit_rate}",
    ]
    logger.debug(f"服务器启动命令: adb {' '.join(cmd)}")
    return _popen_adb(cmd, stdout=subprocess.DEVNULL)


def check_file_exists(remote_path):
    """
    检查设备上指定路径的文件是否存在。
    """
    result = _run_adb(["shell", "test", "-f", remote_path, "&&", "echo", "exists"])
    return result.stdout.strip() == "exists"


def take_screenshot():
    """
    通过 adb exec-out screencap 截取设备屏幕，返回 PNG 二进制数据。
    """
    from .utils import find_adb_path

    adb_path = find_adb_path()
    cmd = [adb_path, "exec-out", "screencap", "-p"]
    logger.debug(f"执行截图命令: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode != 0:
        err = result.stderr.decode(errors='replace').strip()
        raise RuntimeError(f"截图失败: {err}")
    return result.stdout
