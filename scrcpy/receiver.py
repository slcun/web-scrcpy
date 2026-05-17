"""数据接收线程"""

import config
import logging

logger = logging.getLogger('web-scrcpy')


def receive_video(sock, callback, video_codec, stop_flag):
    """视频接收循环"""
    logger.info(f"开始接收视频数据 ({video_codec.upper()})...")
    try:
        sock.recv(1)
        logger.debug("视频连接确认完成")

        total_received = 0
        frames = 0
        while not stop_flag():
            data = sock.recv(config.VIDEO_RECV_SIZE)
            if not data:
                logger.debug("视频数据连接关闭")
                break
            total_received += len(data)
            frames += 1
            callback(data)
            if frames <= 3:
                logger.info(f"视频数据块 #{frames}: {len(data)} 字节, 前20字节: {data[:20].hex()}")
        logger.info(f"视频数据接收停止, 累计接收: {total_received} 字节, 总帧数: {frames}")
    except Exception as e:
        logger.error(f"接收视频数据异常: {e}")


def receive_audio(sock, stop_flag):
    """音频接收循环（目前仅计数不转发）"""
    logger.info("开始接收音频数据...")
    try:
        sock.recv(1)
        logger.debug("音频连接确认完成")

        total_received = 0
        while not stop_flag():
            data = sock.recv(config.AUDIO_RECV_SIZE)
            if not data:
                logger.debug("音频数据连接关闭")
                break
            total_received += len(data)
        logger.info(f"音频数据接收停止, 累计接收: {total_received} 字节")
    except Exception as e:
        logger.error(f"接收音频数据异常: {e}")


def receive_control(sock, stop_flag):
    """控制连接接收循环"""
    logger.info("控制连接已建立...")
    try:
        sock.recv(1)
        logger.debug("控制连接确认完成")

        while not stop_flag():
            data = sock.recv(config.CONTROL_RECV_SIZE)
            if not data:
                logger.debug("控制连接关闭")
                break
            logger.debug(f"收到控制消息, 长度: {len(data)}")
        logger.info("控制连接停止")
    except Exception as e:
        logger.error(f"控制连接异常: {e}")
