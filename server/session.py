"""客户端会话管理，封装全局状态"""

import queue
import logging

logger = logging.getLogger('web-scrcpy')


class ClientSession:
    """封装单个客户端会话的所有状态"""

    def __init__(self):
        self.sid = None
        self.scrcpy = None
        self.message_queue = queue.Queue()

    def connect(self, sid):
        """建立会话"""
        self.sid = sid

    def disconnect(self):
        """断开会话，清理资源"""
        self.sid = None
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except queue.Empty:
                break

    @property
    def is_active(self):
        """会话是否活跃"""
        return self.sid is not None

    def feed_video_data(self, data):
        """往消息队列放入视频数据（由 scrcpy 回调）"""
        if self.is_active:
            self.message_queue.put(data)
