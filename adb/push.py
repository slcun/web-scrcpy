"""文件传输：adb push 操作"""

from .utils import _run_adb, logger
from .errors import AdbPushFailed


def push_file(local_path, remote_path):
    """
    将本地文件推送到 Android 设备。
    local_path: 本地文件路径
    remote_path: 设备目标路径
    """
    logger.info(f"推送 {local_path} 到设备 {remote_path}...")
    result = _run_adb(["push", local_path, remote_path])
    if result.returncode != 0:
        raise AdbPushFailed(f"推送文件失败: {result.stderr}")
    logger.info("文件推送成功")
