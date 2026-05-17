"""SocketIO 事件处理器"""

import base64
from flask import request
from scrcpy import Scrcpy
from adb.shell import take_screenshot
import config
import logging

logger = logging.getLogger('web-scrcpy')


def register(socketio, session, video_relay, video_bit_rate=None, video_codec=None):
    """注册所有 SocketIO 事件处理器到 socketio 实例"""
    bit_rate = video_bit_rate or config.VIDEO_BIT_RATE
    codec = video_codec or config.VIDEO_CODEC

    @socketio.on('connect')
    def handle_connect():
        """处理客户端连接请求"""
        logger.info(f"客户端连接请求, SID: {request.sid}")

        if session.is_active:
            logger.warning(f"拒绝连接: 已有客户端连接 (sid={session.sid})")
            return False

        session.connect(request.sid)
        logger.info(f"接受连接, SID: {session.sid}, 视频码率: {bit_rate}, 编码: {codec}")
        socketio.emit('codec_info', {'codec': codec}, to=session.sid)

        try:
            scrcpy = Scrcpy()
            session.scrcpy = scrcpy
            scrcpy.scrcpy_start(session.feed_video_data, bit_rate, codec)
            socketio.start_background_task(video_relay.run)
            logger.info(f"连接完成, scrcpy: {scrcpy}")
        except Exception as e:
            logger.error(f"启动 Scrcpy 服务失败: {e}")
            session.scrcpy = None
            session.disconnect()
            return False

    @socketio.on('disconnect')
    def handle_disconnect():
        """处理客户端断开连接"""
        logger.info(f"客户端断开连接, SID: {session.sid}")
        if session.scrcpy:
            session.scrcpy.scrcpy_stop()
            session.scrcpy = None
        session.disconnect()
        logger.info("Scrcpy 服务已停止")

    @socketio.on('control_data')
    def handle_control_data(data):
        """处理控制数据（触摸/按键），直接转发到设备"""
        if session.scrcpy:
            session.scrcpy.scrcpy_send_control(data)
            logger.debug(f"发送控制数据, 长度: {len(data)}")

    @socketio.on('screenshot')
    def handle_screenshot(_data=None):
        """截图并返回 PNG 数据"""
        if not session.is_active:
            logger.warning("截图请求被拒绝: 无活动会话")
            return {'error': '无活动会话'}
        try:
            png_data = take_screenshot()
            b64 = base64.b64encode(png_data).decode('ascii')
            logger.info(f"截图成功, 大小: {len(png_data)} bytes")
            return {'data': b64}
        except Exception as e:
            logger.error(f"截图失败: {e}")
            return {'error': str(e)}
