"""Scrcpy 服务编排"""

from threading import Thread
import time
import config
import logging
from adb import AdbClient
from . import connection as conn
from . import receiver as recv
from . import control as ctrl

logger = logging.getLogger('web-scrcpy')


class Scrcpy:
    """Scrcpy 服务器管理器，负责与 Android 设备的通信"""

    def __init__(self):
        self.adb = AdbClient()
        self.sockets = {}
        self.threads = {}
        self.android_process = None
        self.android_thread = None
        self.stop = False
        self.video_bit_rate = None
        self.video_codec = None
        self.video_callback = None

    def _read_server_stderr(self):
        """读取 scrcpy server 的 stderr 输出"""
        while not self.stop:
            stderr_line = self.android_process.stderr.readline().decode().strip()
            if not stderr_line:
                break
            if stderr_line:
                logger.warning(f"服务器输出: {stderr_line}")
        self.android_process.wait()
        logger.info("Scrcpy 服务器停止")

    def scrcpy_start(self, video_callback, video_bit_rate, video_codec=None):
        """启动 Scrcpy 服务"""
        self.video_bit_rate = video_bit_rate
        self.video_codec = video_codec or config.VIDEO_CODEC
        self.video_callback = video_callback
        self.stop = False
        logger.info(f"启动 Scrcpy 服务, 码率: {video_bit_rate}, 编码: {self.video_codec}")

        try:
            self.adb.check_device()
        except Exception as e:
            logger.error(f"设备检测失败: {e}")
            return

        try:
            self.adb.push_server(config.SCRCPY_SERVER_PATH, config.DEVICE_SERVER_PATH)
        except Exception as e:
            logger.error(f"推送服务器文件失败: {e}")
            return

        try:
            self.adb.setup_forward(config.LOCAL_PORT)
        except Exception as e:
            logger.error(f"端口转发设置失败: {e}")
            return

        self.android_process = self.adb.start_server(self.video_bit_rate, self.video_codec)
        self.android_thread = Thread(target=self._read_server_stderr, daemon=True)
        self.android_thread.start()

        # 等服务器完成初始化（adb shell 启动 Java 需要时间）
        time.sleep(1)

        # 建立三条连接（带重试）
        try:
            logger.info("建立视频连接...")
            self.sockets['video'] = conn.connect_with_retry('localhost', config.LOCAL_PORT, nodelay=True)
            logger.info("视频连接建立成功")

            logger.info("建立音频连接...")
            self.sockets['audio'] = conn.connect_with_retry('localhost', config.LOCAL_PORT)
            logger.info("音频连接建立成功")

            logger.info("建立控制连接...")
            self.sockets['control'] = conn.connect_with_retry('localhost', config.LOCAL_PORT)
            logger.info("控制连接建立成功")
        except ConnectionError as e:
            logger.error(f"建立连接失败: {e}")
            self.scrcpy_stop()
            return

        logger.info("启动后台线程...")
        self.threads['video'] = Thread(
            target=recv.receive_video,
            args=(self.sockets['video'], self.video_callback, self.video_codec, lambda: self.stop),
            daemon=True
        )
        self.threads['audio'] = Thread(
            target=recv.receive_audio,
            args=(self.sockets['audio'], lambda: self.stop),
            daemon=True
        )
        self.threads['control'] = Thread(
            target=recv.receive_control,
            args=(self.sockets['control'], lambda: self.stop),
            daemon=True
        )
        self.threads['video'].start()
        self.threads['audio'].start()
        self.threads['control'].start()
        logger.info("Scrcpy 服务启动完成")

    def scrcpy_stop(self):
        """停止 Scrcpy 服务"""
        logger.info("停止 Scrcpy 服务...")
        self.stop = True

        for name in ('video', 'audio', 'control'):
            conn.close_socket(self.sockets.pop(name, None), name)

        for name in ('video', 'audio', 'control'):
            t = self.threads.pop(name, None)
            if t:
                t.join(timeout=5)
                if t.is_alive():
                    logger.warning(f"{name} 线程未在超时内退出")

        if self.android_process:
            self.android_process.terminate()
            logger.debug("设备端进程已终止")

        if self.android_thread:
            self.android_thread.join(timeout=5)
            if self.android_thread.is_alive():
                logger.warning("设备端服务器线程未在超时内退出")

        self.adb.cleanup_forward(config.LOCAL_PORT)
        logger.info("Scrcpy 服务已停止")

    def scrcpy_send_control(self, data):
        """发送控制数据到设备"""
        ctrl.send_control(self.sockets.get('control'), data)
