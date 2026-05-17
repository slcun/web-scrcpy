"""Socket 连接管理"""

import socket
import time
import logging

logger = logging.getLogger('web-scrcpy')

DEFAULT_TIMEOUT = 10
ATTEMPT_TIMEOUT = 2
RETRY_INTERVAL = 0.1


def create_tcp_socket(nodelay=False):
    """创建 TCP socket"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if nodelay:
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    return sock


def _remaining_timeout(start, total):
    """计算剩余超时时间，至少保留一个 ATTEMPT_TIMEOUT 窗口"""
    elapsed = time.time() - start
    remaining = total - elapsed
    return max(ATTEMPT_TIMEOUT, remaining)


def connect_with_retry(host, port, nodelay=False, timeout=DEFAULT_TIMEOUT):
    """连接 TCP 端口，失败时重试直到超时"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            sock = create_tcp_socket(nodelay)
            sock.settimeout(_remaining_timeout(start, timeout))
            sock.connect((host, port))
            sock.settimeout(None)
            return sock
        except (ConnectionRefusedError, OSError):
            if time.time() - start >= timeout:
                break
            time.sleep(RETRY_INTERVAL)
    raise ConnectionError(f"连接 {host}:{port} 超时（{timeout}s）")


def close_socket(sock, name="socket"):
    """安全关闭 socket"""
    if sock is None:
        return
    try:
        sock.shutdown(socket.SHUT_RDWR)
    except Exception:
        pass
    try:
        sock.close()
    except Exception as e:
        logger.warning(f"关闭 {name} socket 失败: {e}")
