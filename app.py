from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, send
from scrcpy import Scrcpy
import argparse
import queue
import config
import logging
from logging.handlers import RotatingFileHandler
import os

def setup_logging():
    """初始化日志配置"""
    logger = logging.getLogger('web-scrcpy')
    logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    formatter = logging.Formatter(config.LOG_FORMAT)
    
    # 控制台输出
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件输出
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

logger = setup_logging()

scpy_ctx = None
client_sid = None
message_queue = queue.Queue()
video_bit_rate = config.VIDEO_BIT_RATE

app = Flask(__name__)
app.config['SECRET_KEY'] = config.SECRET_KEY
socketio = SocketIO(app, async_mode=None)

@app.route('/')
def index():
    return render_template('index.html')

def video_send_task():
    """视频数据发送任务：从消息队列获取数据并发送给客户端"""
    global client_sid
    logger.info("视频发送任务启动")
    while client_sid != None:
        try:
            message = message_queue.get(timeout=0.01)
            socketio.emit('video_data', message, to=client_sid)
        except queue.Empty:
            pass
        except Exception as e:
            logger.error(f"发送视频数据失败: {e}")
        finally:
            socketio.sleep(0.001)
    logger.info("视频发送任务停止")

def send_video_data(data):
    message_queue.put(data)

@socketio.on('connect')
def handle_connect():
    """处理客户端连接请求"""
    global scpy_ctx, client_sid
    logger.info(f"客户端连接请求, SID: {request.sid}")

    if scpy_ctx is not None:
        logger.warning(f"拒绝连接: 已有客户端连接 (scpy_ctx={scpy_ctx})")
        return False
    else:
        client_sid = request.sid
        logger.info(f"接受连接, SID: {client_sid}, 视频码率: {video_bit_rate}")
        scpy_ctx = Scrcpy()
        scpy_ctx.scrcpy_start(send_video_data, video_bit_rate)
        socketio.start_background_task(video_send_task)
        logger.info(f"连接完成, scpy_ctx: {scpy_ctx}")

@socketio.on('disconnect')
def handle_disconnect():
    """处理客户端断开连接"""
    global scpy_ctx, client_sid
    logger.info(f"客户端断开连接, SID: {client_sid}, scpy_ctx: {scpy_ctx}")
    client_sid = None
    if scpy_ctx:
        scpy_ctx.scrcpy_stop()
        scpy_ctx = None
    logger.info("Scrcpy 服务已停止")

@socketio.on('control_data')
def handle_control_data(data):
    """处理控制数据"""
    global scpy_ctx
    if scpy_ctx:
        scpy_ctx.scrcpy_send_control(data)
        logger.debug(f"发送控制数据, 长度: {len(data)}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web server for scrcpy')
    parser.add_argument('--video_bit_rate', default=config.VIDEO_BIT_RATE, help='scrcpy video bit rate')
    args = parser.parse_args()
    video_bit_rate = args.video_bit_rate
    logger.info(f"启动 Web-Scrcpy 服务器, 主机: {config.HOST}, 端口: {config.PORT}, 视频码率: {video_bit_rate}")
    socketio.run(app, host=config.HOST, port=config.PORT)