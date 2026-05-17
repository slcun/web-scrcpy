import argparse
import config
from server import create_app

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Web server for scrcpy')
    parser.add_argument('--video_bit_rate', default=config.VIDEO_BIT_RATE, help='scrcpy video bit rate')
    parser.add_argument('--video_codec', default=config.VIDEO_CODEC, help='scrcpy video codec (h264 or h265)')
    args = parser.parse_args()

    app, socketio = create_app(bit_rate=args.video_bit_rate, codec=args.video_codec)
    socketio.run(app, host=config.HOST, port=config.PORT)
