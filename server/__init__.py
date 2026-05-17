"""Web-Scrcpy 服务器"""

import config
import logging
from logging.handlers import RotatingFileHandler
import os
from flask import Flask, render_template
from flask_socketio import SocketIO
from .session import ClientSession
from .video_relay import VideoRelay
from . import handlers

# 当前会话（单客户端限制）
session = ClientSession()


def setup_logging():
    """初始化日志配置"""
    logger = logging.getLogger('web-scrcpy')
    logger.setLevel(getattr(logging, config.LOG_LEVEL))

    # 避免重复添加 handler
    if logger.hasHandlers():
        logger.handlers.clear()

    formatter = logging.Formatter(config.LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if config.LOG_FILE:
        log_dir = os.path.dirname(config.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir)

        file_handler = RotatingFileHandler(
            config.LOG_FILE,
            maxBytes=config.LOG_MAX_BYTES,
            backupCount=config.LOG_BACKUP_COUNT,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def create_app(bit_rate=None, codec=None):
    """应用工厂：创建 Flask app 和 SocketIO 实例，注册路由和事件处理器"""
    setup_logging()

    # 项目根目录（server/__init__.py 的上级）
    _root = os.path.dirname(os.path.dirname(__file__))
    app = Flask(__name__,
                static_folder=os.path.join(_root, 'static'),
                template_folder=os.path.join(_root, 'templates'))
    app.config['SECRET_KEY'] = config.SECRET_KEY

    socketio = SocketIO(app, async_mode=None)

    video_relay = VideoRelay(session, socketio)
    handlers.register(socketio, session, video_relay, bit_rate, codec)

    @app.route('/')
    def index():
        return render_template('index.html')

    return app, socketio
