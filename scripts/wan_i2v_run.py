#!/usr/bin/env python3
"""Minimal headless WAN 2.2 I2V runner: one start frame + motion prompt -> one mp4.

Drives the fp8 wan22_i2v_a14b workflow over the ComfyUI HTTP API by patching nodes
by class_type. Unbuffered, no serve loop, no interactive prompt — safe for unattended
batch use. Designed to be called once per shot; the caller sequences shots.

Usage:
    wan_i2v_run.py <image> <out.mp4> "<prompt>" [frames] [fps] [w] [h] [seed]
"""
import json, sys, time, urllib.request, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
REPO = Path("/media/menser/fauna/image_gen")
WF = REPO / "workflows" / "wan22_i2v_a14b.json"
OUT = REPO / "comfyui" / "output"
NEG = ("bright tones, overexposed, static, blurred details, subtitles, worst quality, "
       "low quality, jpeg artifacts, watermark, text")

def log(m): print(m, flush=True)

def upload(path):
    path = Path(path); data = path.read_bytes(); b = uuid.uuid4().hex
    body = (f"--{b}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{path.name}\"\r\n"
            f"Content-Type: application/octet-stream\r\n\r\n").encode() + data + f"\r\n--{b}--\r\n".encode()
    req = urllib.request.Request(f"{SERVER}/upload/image", data=body,
                                 headers={"Content-Type": f"multipart/form-data; boundary={b}"})
    return json.loads(urllib.request.urlopen(req).read())["name"]

def set_in(w, cls, key, val, all_nodes=False):
    ids = [n for n, d in w.items() if d.get("class_type") == cls]
    for n in (ids if all_nodes else ids[:1]):
        if isinstance(w[n]["inputs"].get(key), list):
            raise ValueError(f"{cls}.{key} is a link, not a literal")
        w[n]["inputs"][key] = val

def main():
    img, out, prompt = sys.argv[1], sys.argv[2], sys.argv[3]
    frames = int(sys.argv[4]) if len(sys.argv) > 4 else 49
    fps    = int(sys.argv[5]) if len(sys.argv) > 5 else 16
    w_     = int(sys.argv[6]) if len(sys.argv) > 6 else 832
    h_     = int(sys.argv[7]) if len(sys.argv) > 7 else 480
    seed   = int(sys.argv[8]) if len(sys.argv) > 8 else 42

    wf = json.loads(WF.read_text())
    name = upload(img); log(f"uploaded {name}")
    set_in(wf, "LoadImage", "image", name)
    set_in(wf, "WanVideoTextEncode", "positive_prompt", prompt)
    set_in(wf, "WanVideoTextEncode", "negative_prompt", NEG)
    set_in(wf, "ImageResizeKJv2", "width", w_)
    set_in(wf, "ImageResizeKJv2", "height", h_)
    set_in(wf, "WanVideoImageToVideoEncode", "num_frames", frames)
    set_in(wf, "WanVideoSampler", "seed", seed, all_nodes=True)
    set_in(wf, "VHS_VideoCombine", "frame_rate", fps)

    body = json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(f"{SERVER}/prompt", data=body, headers={"Content-Type": "application/json"})
    pid = json.loads(urllib.request.urlopen(req).read())["prompt_id"]
    log(f"queued {pid} ({frames}f @ {fps}fps, {w_}x{h_}, seed {seed})")

    deadline = time.time() + 1800
    while time.time() < deadline:
        hist = json.loads(urllib.request.urlopen(f"{SERVER}/history/{pid}").read())
        if pid in hist:
            status = hist[pid].get("status", {})
            if status.get("status_str") == "error":
                log("ERROR: ComfyUI reported execution error"); sys.exit(2)
            for node_out in hist[pid].get("outputs", {}).values():
                for item in node_out.get("gifs", []):
                    p = OUT / item.get("subfolder", "") / item["filename"]
                    if p.exists():
                        Path(out).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(p, out); log(f"SAVED {out}"); return
            log("DONE but no video output found"); sys.exit(3)
        time.sleep(3)
    log("TIMEOUT"); sys.exit(4)

if __name__ == "__main__":
    main()
