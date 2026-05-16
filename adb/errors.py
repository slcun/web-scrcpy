"""ADB 操作相关的自定义异常"""


class AdbError(Exception):
    """ADB 操作基类异常"""


class AdbDeviceNotFound(AdbError):
    """未找到 Android 设备"""


class AdbPushFailed(AdbError):
    """adb push 失败"""


class AdbForwardFailed(AdbError):
    """adb forward 设置失败"""


class AdbShellFailed(AdbError):
    """adb shell 命令执行失败"""
