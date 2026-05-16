"""AdbClient：ADB 操作的高层封装"""

from . import device, push, forward, shell
from .errors import AdbDeviceNotFound, AdbPushFailed, AdbForwardFailed
from .utils import logger


class AdbClient:
    """
    ADB 客户端，封装了所有 ADB 操作。
    提供 check_device、push_server、setup_forward、start_server 等高层接口。
    """

    def check_device(self):
        """
        检查 ADB 设备连接状态。
        """
        return device.check_connected()

    def push_server(self, local_path, remote_path):
        """
        推送 scrcpy-server.jar 到设备。
        """
        push.push_file(local_path, remote_path)

    def setup_forward(self, local_port):
        """
        设置端口转发。
        """
        forward.setup(local_port)

    def start_server(self, video_bit_rate, video_codec):
        """
        启动设备端 scrcpy-server 进程。
        """
        return shell.start_server_process(video_bit_rate, video_codec)

    def cleanup_forward(self, local_port):
        """
        清理端口转发。
        """
        forward.remove(local_port)
