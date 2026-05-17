"""控制数据发送"""

import logging

logger = logging.getLogger('web-scrcpy')


def send_control(sock, data):
    """发送控制数据到设备"""
    if sock is None:
        logger.warning("控制 socket 未就绪，丢弃控制数据")
        return
    try:
        sock.send(data)
        logger.debug(f"发送控制数据成功, 长度: {len(data)}")
    except Exception as e:
        logger.error(f"发送控制数据失败: {e}")
