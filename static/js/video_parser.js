class VideoParser {
    constructor(onNaluCallback, debug = false, codec = 'h264') {
        this.debug = debug
        this.buffer = new Uint8Array(0);
        this.codec = codec.toLowerCase();
        this.name = null;
        this.width = null;
        this.height = null;
        this.hasKeyFrame = null;
        this.sps = null;
        this.pps = null;
        this.vps = null;
        this.mimeCodec = null;
        this.onNaluCallback = onNaluCallback;
        this.hasSentSpsPps = false;
    }

    appendData(data) {
        const newBuffer = new Uint8Array(this.buffer.length + data.length);
        newBuffer.set(this.buffer, 0);
        newBuffer.set(data, this.buffer.length);
        this.buffer = newBuffer;
        this.scrcpyProcessBuffer();
    }

    scrcpyProcessBuffer() {
        let startIndex = 0;
        if (this.name == null) {
            if (this.buffer.length >= 64) {
                const name = this.buffer.slice(0, 64);
                this.name = new TextDecoder().decode(name);
                console.log("Device name:" + this.name);
                if (this.onNaluCallback) {
                    this.onNaluCallback({
                        type: 'name',
                        data: { "name": this.name }
                    });
                }
                startIndex = 64;
            }
        } else if (this.width == null) {
            if (this.buffer.length >= 12) {
                const id = new DataView(this.buffer.buffer).getInt32(0, false);
                this.width = new DataView(this.buffer.buffer).getInt32(4, false);
                this.height = new DataView(this.buffer.buffer).getInt32(8, false);
                if (this.debug) { console.log("[DEBUG] screen_size: " + this.width + "x" + this.height); }
                if (this.onNaluCallback) {
                    this.onNaluCallback({
                        type: 'screen_size',
                        data: { "width": this.width, "height": this.height }
                    });
                }
                startIndex += 12;
            }
        } else while (this.buffer.length - startIndex > 12) {
            const size = new DataView(this.buffer.buffer).getInt32(startIndex + 8, false);
            if (this.buffer.length - startIndex >= 12 + size) {
                const nalu = this.buffer.slice(startIndex + 12, startIndex + 12 + size);
                // if (this.debug) { console.log("[DEBUG] scrcpy frame: scrcpy_size=" + size); }
                this.processBuffer(nalu)
                startIndex = startIndex + 12 + size;
            } else {
                break;
            }
        }
        this.buffer = this.buffer.slice(startIndex);
    }

    findSequence(arr, sequence, startIndex = 0) {
        const seqLength = sequence.length;
        for (let i = startIndex; i <= arr.length - seqLength; i++) {
            let match = true;
            for (let j = 0; j < seqLength; j++) {
                if (arr[i + j] !== sequence[j]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                return i;
            }
        }
        return -1;
    }

    processBuffer(nalu) {
        if (this.codec === 'h265') {
            this.processBufferH265(nalu);
        } else {
            this.processBufferH264(nalu);
        }
    }

    processBufferH264(nalu) {
        const nalu_type = nalu[4] & 0x1f;
        if (nalu_type === 1) {
            if (this.debug)
                console.log("P frame", nalu.length)
        } else if (nalu_type === 5) {
            if (this.debug)
                console.log("I frame", nalu.length)
        } else if (nalu_type === 7) {
            const next_pos = this.findSequence(nalu, [0, 0, 0, 1], 5)
            if (next_pos > 0) {
                this.sps = nalu.slice(0, next_pos)
                if (this.debug)
                    console.log("sps", next_pos)
                this.processBufferH264(nalu.slice(next_pos))
            } else {
                this.sps = nalu
                if (this.debug)
                    console.log("sps", nalu.length)
            }
            let ret = SPSParser.parseSPS(this.sps.slice(4));
            if (this.onNaluCallback) {
                this.onNaluCallback({
                    type: 'size_change',
                    data: {"width" : ret.present_size.width, "height" : ret.present_size.height}
                });
            }
            return;
        } else if (nalu_type === 8) {
            const next_pos = this.findSequence(nalu, [0, 0, 0, 1], 5)
            if (next_pos > 0) {
                this.pps = nalu.slice(0, next_pos)
                if (this.debug)
                    console.log("pps", next_pos)
                this.processBufferH264(nalu.slice(next_pos))
            } else {
                this.pps = nalu
                if (this.debug)
                    console.log("pps", nalu.length)
            }
            return;
        } else if (this.debug) {
            console.log("unknown h264 frame type", nalu[0], nalu[1], nalu[2], nalu[3], nalu_type)
        }

        if (this.pps != null && this.sps != null) {
            if (this.onNaluCallback) {
                this.onNaluCallback({
                    type: 'init',
                    data: { "width:": this.width, " height:": this.height, "pps": this.pps, "sps": this.sps }
                });
            }
            this.pps = null;
            this.sps = null;
        }
        if (this.onNaluCallback) {
            this.onNaluCallback({
                type: 'nalu',
                data: nalu
            });
        }
    }

    processBufferH265(nalu) {
        const nalu_type = (nalu[4] >> 1) & 0x3f;
        if (nalu_type === 0) {
        } else if (nalu_type === 1) {
        } else if (nalu_type === 19 || nalu_type === 20) {
        } else if (nalu_type === 32) {
            const next_pos = this.findSequence(nalu, [0, 0, 0, 1], 5)
            if (next_pos > 0) {
                this.vps = nalu.slice(0, next_pos)
                this.processBufferH265(nalu.slice(next_pos))
            } else {
                this.vps = nalu
            }
            return;
        } else if (nalu_type === 33) {
            const next_pos = this.findSequence(nalu, [0, 0, 0, 1], 5)
            if (next_pos > 0) {
                this.sps = nalu.slice(0, next_pos)
                this.processBufferH265(nalu.slice(next_pos))
            } else {
                this.sps = nalu
            }
            let ret = this.parseH265SPS(this.sps.slice(4));
            if (this.onNaluCallback) {
                this.onNaluCallback({
                    type: 'size_change',
                    data: {"width" : ret.width, "height" : ret.height}
                });
            }
            return;
        } else if (nalu_type === 34) {
            const next_pos = this.findSequence(nalu, [0, 0, 0, 1], 5)
            if (next_pos > 0) {
                this.pps = nalu.slice(0, next_pos)
                this.processBufferH265(nalu.slice(next_pos))
            } else {
                this.pps = nalu
            }
            return;
        }

        if (this.pps != null && this.sps != null && this.vps != null) {
            if (this.debug) { console.log("[DEBUG] H265 init callback FIRING"); }
            if (this.onNaluCallback) {
                this.onNaluCallback({
                    type: 'init',
                    data: { "width:": this.width, " height:": this.height, "pps": this.pps, "sps": this.sps, "vps": this.vps }
                });
            }
            this.vps = null;
            this.pps = null;
            this.sps = null;
        }
        if (this.onNaluCallback) {
            this.onNaluCallback({
                type: 'nalu',
                data: nalu
            });
        }
    }

    removeEmulationPrevention(data) {
        const out = [];
        for (let i = 0; i < data.length; i++) {
            if (i >= 2 && data[i - 2] === 0x00 && data[i - 1] === 0x00 && data[i] === 0x03) {
                continue;
            }
            out.push(data[i]);
        }
        return new Uint8Array(out);
    }

    parseH265SPS(data) {
        data = this.removeEmulationPrevention(data);
        const gb = new ExpGolomb(data);
        gb.readByte();
        gb.readByte();
        gb.readBits(4);
        gb.readBits(3);
        gb.readBits(1);
        gb.readBits(2);
        gb.readBits(1);
        gb.readBits(5);
        gb.readBits(32);
        for (let i = 0; i < 6; i++) gb.readBits(8);
        gb.readBits(8);
        gb.readUEG();
        let chroma_format_idc = gb.readUEG();
        if (chroma_format_idc === 3) gb.readBits(1);
        let pic_width_in_luma_samples = gb.readUEG();
        let pic_height_in_luma_samples = gb.readUEG();
        let conformance_window_flag = gb.readBool();
        let conf_win_left_offset = 0, conf_win_right_offset = 0;
        let conf_win_top_offset = 0, conf_win_bottom_offset = 0;
        if (conformance_window_flag) {
            conf_win_left_offset = gb.readUEG();
            conf_win_right_offset = gb.readUEG();
            conf_win_top_offset = gb.readUEG();
            conf_win_bottom_offset = gb.readUEG();
        }
        let sub_width_c = (chroma_format_idc === 1 || chroma_format_idc === 2) ? 2 : 1;
        let sub_height_c = (chroma_format_idc === 1) ? 2 : 1;
        let width = pic_width_in_luma_samples - sub_width_c * (conf_win_right_offset + conf_win_left_offset);
        let height = pic_height_in_luma_samples - sub_height_c * (conf_win_top_offset + conf_win_bottom_offset);
        gb.destroy();
        return { width, height };
    }
}
