from threading import Thread
import socket
import time
import config
import logging
from adb import AdbClient

logger = logging.getLogger('web-scrcpy')


class Scrcpy:
    """Scrcpy 服务器管理类，负责与 Android 设备的通信"""

    def __init__(self):
        self.adb = AdbClient()

        self.video_socket = None
        self.audio_socket = None
        self.control_socket = None

        self.android_thread = None
        self.video_thread = None
        self.audio_thread = None
        self.control_thread = None
        self.android_process = None
        self.stop = False
        self.video_bit_rate = None
        self.video_codec = None
        self.video_callback = None

    def start_server(self):
        """在设备上启动 scrcpy 服务器"""
        self.android_process = self.adb.start_server(self.video_bit_rate, self.video_codec)
        # 读取并输出 stderr（scrcpy server 的日志输出）
        while not self.stop:
            stderr_line = self.android_process.stderr.readline().decode().strip()
            if not stderr_line:
                break
            if stderr_line:
                logger.warning(f"服务器输出: {stderr_line}")
        self.android_process.wait()
        logger.info("Scrcpy 服务器停止")

    def receive_video_data(self):
        """接收视频数据"""
        logger.info(f"开始接收视频数据 ({self.video_codec.upper()})...")
        try:
            self.video_socket.recv(1)  # 接收连接确认字节
            logger.debug("视频连接确认完成")

            total_received = 0
            frames = 0
            while not self.stop:
                data = self.video_socket.recv(config.VIDEO_RECV_SIZE)
                if not data:
                    logger.debug("视频数据连接关闭")
                    break
                total_received += len(data)
                frames += 1
                self.video_callback(data)
                if frames <= 3:
                    logger.info(f"视频数据块 #{frames}: {len(data)} 字节, 前20字节: {data[:20].hex()}")
            logger.info(f"视频数据接收停止, 累计接收: {total_received} 字节, 总帧数: {frames}")
        except Exception as e:
            logger.error(f"接收视频数据异常: {e}")

    def receive_audio_data(self):
        """接收音频数据"""
        logger.info("开始接收音频数据...")
        try:
            self.audio_socket.recv(1)  # 接收连接确认字节
            logger.debug("音频连接确认完成")

            total_received = 0
            while not self.stop:
                data = self.audio_socket.recv(config.AUDIO_RECV_SIZE)
                if not data:
                    logger.debug("音频数据连接关闭")
                    break
                total_received += len(data)
            logger.info(f"音频数据接收停止, 累计接收: {total_received} 字节")
        except Exception as e:
            logger.error(f"接收音频数据异常: {e}")

    def handle_control_conn(self):
        """处理控制连接"""
        logger.info("控制连接已建立...")
        try:
            self.control_socket.recv(1)  # 接收连接确认字节
            logger.debug("控制连接确认完成")

            while not self.stop:
                data = self.control_socket.recv(config.CONTROL_RECV_SIZE)
                if not data:
                    logger.debug("控制连接关闭")
                    break
                logger.debug(f"收到控制消息, 长度: {len(data)}")
            logger.info("控制连接停止")
        except Exception as e:
            logger.error(f"控制连接异常: {e}")

    def scrcpy_start(self, video_callback, video_bit_rate, video_codec=None):
        """启动 Scrcpy 服务"""
        self.video_bit_rate = video_bit_rate
        self.video_codec = video_codec or config.VIDEO_CODEC
        self.video_callback = video_callback
        self.stop = False
        logger.info(f"启动 Scrcpy 服务, 码率: {video_bit_rate}, 编码: {self.video_codec}")

        # 检测设备
        try:
            self.adb.check_device()
        except Exception as e:
            logger.error(f"设备检测失败: {e}")
            return

        # 推送服务器
        try:
            self.adb.push_server(config.SCRCPY_SERVER_PATH, config.DEVICE_SERVER_PATH)
        except Exception as e:
            logger.error(f"推送服务器文件失败: {e}")
            return

        # 设置端口转发
        try:
            self.adb.setup_forward(config.LOCAL_PORT)
        except Exception as e:
            logger.error(f"端口转发设置失败: {e}")
            return

        # 启动设备端服务器
        logger.info("启动设备端服务器线程...")
        self.android_thread = Thread(target=self.start_server, daemon=True)
        self.android_thread.start()
        time.sleep(1)

        # video connection
        logger.info("建立视频连接...")
        self.video_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.video_socket.connect(('localhost', config.LOCAL_PORT))
        logger.info("视频连接建立成功")

        # audio connection
        logger.info("建立音频连接...")
        self.audio_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.audio_socket.connect(('localhost', config.LOCAL_PORT))
        logger.info("音频连接建立成功")

        # control connection
        logger.info("建立控制连接...")
        self.control_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.control_socket.connect(('localhost', config.LOCAL_PORT))
        logger.info("控制连接建立成功")

        logger.info("启动后台线程...")
        self.video_thread = Thread(target=self.receive_video_data, daemon=True)
        self.audio_thread = Thread(target=self.receive_audio_data, daemon=True)
        self.control_thread = Thread(target=self.handle_control_conn, daemon=True)
        self.video_thread.start()
        self.audio_thread.start()
        self.control_thread.start()
        logger.info("Scrcpy 服务启动完成")

    def scrcpy_stop(self):
        """停止 Scrcpy 服务"""
        logger.info("停止 Scrcpy 服务...")
        self.stop = True

        try:
            self.video_socket.shutdown(socket.SHUT_RDWR)
            self.video_socket.close()
            logger.debug("视频 socket 关闭成功")
        except Exception as e:
            logger.error(f"关闭视频 socket 失败: {e}")

        try:
            self.audio_socket.shutdown(socket.SHUT_RDWR)
            self.audio_socket.close()
            logger.debug("音频 socket 关闭成功")
        except Exception as e:
            logger.error(f"关闭音频 socket 失败: {e}")

        try:
            self.control_socket.shutdown(socket.SHUT_RDWR)
            self.control_socket.close()
            logger.debug("控制 socket 关闭成功")
        except Exception as e:
            logger.error(f"关闭控制 socket 失败: {e}")

        logger.debug("等待后台线程结束...")
        self.video_thread.join()
        self.audio_thread.join()
        self.control_thread.join()

        if self.android_process:
            self.android_process.terminate()
            logger.debug("设备端进程已终止")

        self.android_thread.join()
        self.adb.cleanup_forward(config.LOCAL_PORT)
        logger.info("Scrcpy 服务已停止")

    def scrcpy_send_control(self, data):
        """发送控制数据到设备"""
        try:
            self.control_socket.send(data)
            logger.debug(f"发送控制数据成功, 长度: {len(data)}")
        except Exception as e:
            logger.error(f"发送控制数据失败: {e}")
