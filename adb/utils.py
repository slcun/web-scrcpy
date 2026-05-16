"""ADB 工具函数：查找 adb 路径、执行 ADB 命令"""

import os
import subprocess
import logging

logger = logging.getLogger('web-scrcpy')


def find_adb_path():
    """
    查找 ADB 可执行文件路径。
    查找顺序：
      1. adb/adb.exe（当前 adb 模块目录）
      2. scrcpy/adb.exe（旧位置，向后兼容）
      3. PATH 中的 adb
    """
    base = os.path.dirname(os.path.dirname(__file__))
    candidates = [
        os.path.join(base, "adb", "adb.exe"),
        os.path.join(base, "scrcpy", "adb.exe"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return "adb"


def _run_adb(args, check=False, capture_output=True, text=True):
    """
    执行 ADB 命令的底层封装。
    args: 命令参数列表（不包含 adb 路径本身）
    """
    adb_path = find_adb_path()
    cmd = [adb_path] + args
    logger.debug(f"执行 ADB 命令: {' '.join(cmd)}")
    return subprocess.run(cmd, check=check, capture_output=capture_output, text=text)


def _popen_adb(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE):
    """
    启动 ADB 命令的子进程（用于长时间运行的 adb shell 等）。
    """
    adb_path = find_adb_path()
    cmd = [adb_path] + args
    logger.debug(f"启动 ADB 进程: {' '.join(cmd)}")
    return subprocess.Popen(cmd, stdout=stdout, stderr=stderr)
