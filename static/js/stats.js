/* 视频统计面板（码率/帧率/分辨率/编码） */

const statsTracker = {
    sampleInterval: 2,
    bytesReceived: 0,
    frameCount: 0,
    samples: [],
    width: 0,
    height: 0,
    codec: '',

    onFrame(bytes) {
        this.bytesReceived += bytes;
        this.frameCount++;
    },

    onResolution(w, h) {
        this.width = w;
        this.height = h;
    },

    tick() {
        this.samples.push({ bytes: this.bytesReceived, frames: this.frameCount });
        if (this.samples.length > this.sampleInterval) {
            this.samples.shift();
        }
        this.updateDisplay();
    },

    updateDisplay() {
        const bitrateEl = document.getElementById('stats-bitrate');
        const fpsEl = document.getElementById('stats-fps');
        const resEl = document.getElementById('stats-resolution');
        const codecEl = document.getElementById('stats-codec');
        if (!bitrateEl) return;

        if (this.samples.length >= 2) {
            const a = this.samples[0];
            const b = this.samples[this.samples.length - 1];
            const dt = this.sampleInterval;
            const bitrate = (b.bytes - a.bytes) * 8 / dt;
            const fps = (b.frames - a.frames) / dt;
            bitrateEl.textContent = bitrate > 1e6
                ? (bitrate / 1e6).toFixed(1) + ' Mbps'
                : (bitrate / 1e3).toFixed(0) + ' Kbps';
            fpsEl.textContent = fps.toFixed(1) + ' FPS';
        }
        resEl.textContent = this.width + ' × ' + this.height;
        codecEl.textContent = this.codec;
    }
};
