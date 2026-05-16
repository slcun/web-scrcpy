"""端口转发：adb forward 操作"""

from .utils import _run_adb, logger
from .errors import AdbForwardFailed


def setup(local_port, remote="localabstract:scrcpy"):
    """
    设置 ADB 端口转发。
    local_port: 本地 TCP 端口
    remote: 远程地址（默认 localabstract:scrcpy）
    """
    logger.info(f"设置 ADB 端口转发: tcp:{local_port} -> {remote}")
    try:
        _run_adb(["forward", f"tcp:{local_port}", remote], check=True)
        logger.info("ADB 端口转发设置成功")
    except Exception as e:
        raise AdbForwardFailed(f"ADB 端口转发设置失败: {e}")


def remove(local_port):
    """
    移除指定本地端口的 ADB 转发。
    """
    logger.info(f"移除 ADB 端口转发: tcp:{local_port}")
    try:
        _run_adb(["forward", "--remove", f"tcp:{local_port}"], check=True)
        logger.info("ADB 端口转发移除成功")
    except Exception as e:
        logger.error(f"ADB 端口转发移除失败: {e}")
