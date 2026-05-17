/* 主入口：SocketIO + JMuxer + VideoParser 编排 */

const videoElement = document.getElementById('player');
let jmuxer = null;
let parser = null;
let input = null;
let initDone = false;
let pendingBuffer = [];

/* Tooltip 管理（mouseenter/mouseleave，避开 pointer-events:none 问题） */
(function () {
    const tip = document.createElement('div');
    tip.className = 'ctrl-tip';
    document.body.appendChild(tip);
    let hideTimer = null;

    function showTip(btn) {
        const text = btn.getAttribute('data-tip');
        if (!text) return;
        clearTimeout(hideTimer);
        tip.textContent = text;
        tip.style.display = 'block';
        const r = btn.getBoundingClientRect();
        tip.style.top = (r.top + r.height / 2 - tip.offsetHeight / 2) + 'px';
        tip.style.left = (r.left - tip.offsetWidth - 12) + 'px';
    }

    function hideTip() {
        clearTimeout(hideTimer);
        hideTimer = setTimeout(() => { tip.style.display = 'none'; }, 50);
    }

    document.querySelectorAll('.ctrl-btn').forEach((btn) => {
        btn.addEventListener('mouseenter', () => showTip(btn));
        btn.addEventListener('mouseleave', hideTip);
        btn.addEventListener('mousedown', () => { tip.style.display = 'none'; });
    });
})();

function createJmuxerAndParser(codec) {
    const isH265 = codec === 'h265';
    const jmuxerCodec = isH265 ? 'H265' : 'H264';
    jmuxer = new JMuxer({
        node: 'player',
        mode: 'video',
        videoCodec: jmuxerCodec,
        flushingTime: 0,
        fps: 60,
        clearBuffer: true,
        onReady: () => {
            document.getElementById('status').textContent = 'MSE done, waiting for data...';
            if (videoElement) {
                videoElement.controls = false;
                videoElement.style.cssText = `
                    -webkit-media-controls: none !important;
                    -moz-controls: none !important;
                    -ms-media-controls: none !important;
                `;
            }
        },
        onError: (err) => {
            document.getElementById('status').textContent = 'MSE Error: ' + err.message;
        }
    });

    parser = new VideoParser(({ type, data }) => {
        if (type === 'nalu') {
            jmuxer.feed({ video: data });
        } else if (type === 'init') {
            if (data.vps) {
                jmuxer.feed({ video: data.vps });
            }
            jmuxer.feed({ video: data.sps });
            jmuxer.feed({ video: data.pps });
        } else if (type === 'screen_size') {
            statsTracker.onResolution(data.width, data.height);
            initInput(data.width, data.height);
        } else if (type === 'size_change') {
            statsTracker.onResolution(data.width, data.height);
            if (input) {
                input.resizeScreen(data.width, data.height);
            }
        }
    }, isH265, codec);

    for (const buf of pendingBuffer) {
        parser.appendData(buf);
    }
    pendingBuffer = [];

    statsTracker.codec = codec.toUpperCase();
    document.getElementById('stats').style.display = 'block';
    initDone = true;
}

function initInput(width, height) {
    function input_data_cb(data) {
        socket.emit('control_data', data);
    }

    input = new ScrcpyInput(input_data_cb, videoElement, width, height, false);

    const powerIcon = document.getElementById('power-icon');
    const volumeDownIcon = document.getElementById('volume-down-icon');
    const volumeUpIcon = document.getElementById('volume-up-icon');
    const backUpIcon = document.getElementById('back-icon');
    const homeUpIcon = document.getElementById('home-icon');
    const menuUpIcon = document.getElementById('menu-icon');

    powerIcon.addEventListener('mousedown', function () {
        input.screen_on_off(0);
    });
    powerIcon.addEventListener('mouseup', function () {
        input.screen_on_off(1);
    });

    volumeDownIcon.addEventListener('mousedown', (event) => {
        input.snedKeyCode(event, 0, 25);
    });
    volumeDownIcon.addEventListener('mouseup', (event) => {
        input.snedKeyCode(event, 1, 25);
    });

    volumeUpIcon.addEventListener('mousedown', (event) => {
        input.snedKeyCode(event, 0, 24);
    });
    volumeUpIcon.addEventListener('mouseup', (event) => {
        input.snedKeyCode(event, 1, 24);
    });

    backUpIcon.addEventListener('mousedown', (event) => {
        input.snedKeyCode(event, 0, 4);
    });
    backUpIcon.addEventListener('mouseup', (event) => {
        input.snedKeyCode(event, 1, 4);
    });
    homeUpIcon.addEventListener('mousedown', (event) => {
        input.snedKeyCode(event, 0, 3);
    });
    homeUpIcon.addEventListener('mouseup', (event) => {
        input.snedKeyCode(event, 1, 3);
    });
    menuUpIcon.addEventListener('mousedown', (event) => {
        input.snedKeyCode(event, 0, 187);
    });
    menuUpIcon.addEventListener('mouseup', (event) => {
        input.snedKeyCode(event, 1, 187);
    });

    /* 截图按钮 */
    const screenshotIcon = document.getElementById('screenshot-icon');
    screenshotIcon.addEventListener('click', () => {
        socket.emit('screenshot', {}, (response) => {
            if (response.error) {
                alert('截图失败: ' + response.error);
                return;
            }
            const byteChars = atob(response.data);
            const byteNums = new Array(byteChars.length);
            for (let i = 0; i < byteChars.length; i++) {
                byteNums[i] = byteChars.charCodeAt(i);
            }
            const blob = new Blob([new Uint8Array(byteNums)], { type: 'image/png' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            const now = new Date();
            const ts = now.getFullYear()
                + String(now.getMonth() + 1).padStart(2, '0')
                + String(now.getDate()).padStart(2, '0') + '-'
                + String(now.getHours()).padStart(2, '0')
                + String(now.getMinutes()).padStart(2, '0')
                + String(now.getSeconds()).padStart(2, '0');
            a.href = url;
            a.download = 'screenshot-' + ts + '.png';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        });
    });
}

const socket = io({
    reconnection: false,
    autoConnect: true
});

socket.on('codec_info', (data) => {
    const codec = data.codec && data.codec.toLowerCase() === 'h265' ? 'h265' : 'h264';
    createJmuxerAndParser(codec);
});

socket.on('video_data', (data) => {
    const newData = new Uint8Array(data);
    statsTracker.onFrame(data.byteLength);
    if (initDone) {
        parser.appendData(newData);
    } else {
        pendingBuffer.push(newData);
    }
});

socket.on('connect', () => {
    document.getElementById('status').textContent = 'connected, waiting for codec info...';
});

socket.addEventListener('close', () => {
    document.getElementById('status').textContent = 'connect closed, please refresh the page to reconnect';
});

socket.addEventListener('error', (error) => {
    document.getElementById('status').textContent = 'websocket error: ' + error.message;
});

videoElement.addEventListener('error', (e) => {
    console.log('[DEBUG] video element error:', videoElement.error ? videoElement.error.message : 'unknown');
});

window.addEventListener('beforeunload', () => {
    socket.disconnect();
});

setInterval(() => statsTracker.tick(), 1000);

document.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
        e.preventDefault();
        const el = document.getElementById('stats');
        el.style.display = el.style.display === 'none' ? 'block' : 'none';
    }
});
