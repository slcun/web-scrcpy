"""视频数据中继：message_queue → SocketIO"""

import queue
import logging

logger = logging.getLogger('web-scrcpy')


class VideoRelay:
    """从会话的消息队列读取数据并通过 SocketIO 发送给客户端"""

    def __init__(self, session, socketio):
        self.session = session
        self.socketio = socketio

    def run(self):
        """在后台线程中运行，持续从队列读取并发送"""
        logger.info("视频发送任务启动")
        while self.session.is_active:
            try:
                message = self.session.message_queue.get(timeout=0.01)
                if not self.session.is_active:
                    break
                self.socketio.emit('video_data', message, to=self.session.sid)
            except queue.Empty:
                pass
            except Exception as e:
                logger.error(f"发送视频数据失败: {e}")
            finally:
                self.socketio.sleep(0.001)
        while not self.session.message_queue.empty():
            try:
                self.session.message_queue.get_nowait()
            except queue.Empty:
                break
        logger.info("视频发送任务停止")
