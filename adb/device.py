"""设备管理：检测 ADB 设备连接"""

from .utils import _run_adb, logger
from .errors import AdbDeviceNotFound


def list_devices():
    """
    执行 adb devices，返回已连接设备列表。
    """
    result = _run_adb(["devices"])
    lines = result.stdout.strip().splitlines()
    devices = []
    for line in lines:
        if line and not line.startswith("List") and not line.endswith("offline"):
            parts = line.split()
            if len(parts) == 2 and parts[1] == "device":
                devices.append(parts[0])
    return devices


def check_connected():
    """
    检查是否有 Android 设备已连接。
    若未连接则抛出 AdbDeviceNotFound 异常。
    """
    logger.info("检查 ADB 设备...")
    devices = list_devices()
    logger.debug(f"ADB 设备列表: {devices}")
    if not devices:
        raise AdbDeviceNotFound("未找到 Android 设备，请通过 USB 连接设备并开启 USB 调试")
    logger.info(f"检测到 Android 设备: {devices[0]}")
    return devices[0]
