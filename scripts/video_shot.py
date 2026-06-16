#!/usr/bin/env python3
"""Video shot driver: shot list -> WAN 2.2 I2V clips -> HTML video gallery in browser.

The video counterpart to storyboard.py. Drives the installed WAN 2.2 I2V
workflow directly over the ComfyUI HTTP API (no MCP required). Each shot
animates a start frame (image-to-video); identity/scene are carried by that
start frame, so render the frame the way you want the clip to look (see the
character-sheet + cinematic-depth craft notes in CLAUDE.md).

Unlike the storyboard workflows, wan22_i2v_a14b.json has no PARAM_* placeholders,
so this driver patches node inputs by class_type instead of by token.

Usage:
    video_shot.py shots.yaml [--keep]

Shot list format (YAML):

    negative_prompt: "..."            # optional; overrides the built-in default
    num_frames: 81                    # clip length in frames
    fps: 16                           # playback / VHS frame_rate
    width: 832                        # start-frame resize (divisible by 32)
    height: 480
    seed: 42                          # base seed; per-shot = base + index
    style_suffix: "..."               # appended to every prompt ("" disables)
    shots:
      - image: ./plates/car_int.png   # start frame (required per shot)
        prompt: "she applies lip gloss, subtle head turn"
      - image: ./plates/street.png
        prompt: "wide, neon rain, slow push-in"
        seed: 9999                     # per-shot override
        num_frames: 121                # per-shot override

Post-processing (per-frame ESRGAN upscale + RIFE interpolation) is intentionally
NOT wired in here — those need custom nodes that aren't part of the base stack.
See the `## Video delivery` notes in CLAUDE.md for the recommended post chain.
"""
import argparse
import atexit
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery  # noqa: E402

REPO = Path("/media/menser/fauna/image_gen")
WORKFLOWS = REPO / "workflows"
COMFY_OUTPUT = REPO / "comfyui" / "output"
SERVER = "http://127.0.0.1:8188"

WORKFLOW = "wan22_i2v_a14b"

# Preflight guard. WAN 14B unquantized OOM-crashed the whole machine (see the
# HARDWARE RED FLAG in CLAUDE.md). If more than this much VRAM is already in use,
# something heavy is co-loaded and WAN cannot share the card — refuse to launch.
GPU_BUSY_THRESHOLD_MB = 2000

# Cinematic craft appended to every clip prompt (see the source-video notes in
# CLAUDE.md): handheld operator life + atmosphere read as "filmed", not generated.
DEFAULT_STYLE_SUFFIX = (
    "cinematic, subtle handheld camera operator movement, volumetric atmospheric haze, "
    "shallow depth of field, natural motion, no flicker"
)

VIDEO_DEFAULTS = {
    "negative_prompt": (
        "bright tones, overexposed, static, blurred details, subtitles, "
        "worst quality, low quality, jpeg artifacts, watermark, text"
    ),
    "num_frames": 81,
    "fps": 16,
    "width": 832,
    "height": 480,
    "style_suffix": DEFAULT_STYLE_SUFFIX,
}


def load_workflow(name):
    return json.loads((WORKFLOWS / f"{name}.json").read_text())


def nodes_by_class(wf, class_type):
    return [nid for nid, n in wf.items() if n.get("class_type") == class_type]


def set_input(wf, class_type, key, value, *, all_nodes=False):
    """Set inputs[key]=value on node(s) of class_type. Skips link inputs (lists)."""
    ids = nodes_by_class(wf, class_type)
    if not ids:
        raise KeyError(f"workflow has no node of class_type {class_type!r}")
    targets = ids if all_nodes else ids[:1]
    for nid in targets:
        if isinstance(wf[nid]["inputs"].get(key), list):
            # a connected link, not a literal — never overwrite a wire
            raise ValueError(f"node {nid} input {key!r} is a link, not a literal")
        wf[nid]["inputs"][key] = value


def queue_prompt(workflow):
    body = json.dumps({"prompt": workflow, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(f"{SERVER}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["prompt_id"]


def wait_for(prompt_id, timeout=1800):
    """Poll history until the prompt completes. Video renders are slow — long timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = urllib.request.urlopen(f"{SERVER}/history/{prompt_id}").read()
        hist = json.loads(resp)
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"prompt {prompt_id} did not complete in {timeout}s")


def first_video_path(result):
    """VHS_VideoCombine reports outputs under the 'gifs' key (mp4/webm included)."""
    for node_out in result.get("outputs", {}).values():
        for item in node_out.get("gifs", []):
            fp = item.get("fullpath")
            if fp and Path(fp).exists():
                return Path(fp)
            p = COMFY_OUTPUT / item.get("subfolder", "") / item["filename"]
            if p.exists():
                return p
    raise FileNotFoundError("no video output found in prompt history")


def upload_image(path):
    path = Path(path).expanduser()
    data = path.read_bytes()
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{SERVER}/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    return json.loads(urllib.request.urlopen(req).read())["name"]


def compose_prompt(prompt, cfg):
    suffix = cfg.get("style_suffix", "")
    return f"{prompt}, {suffix}" if suffix else prompt


def render_shot(shot, cfg):
    wf = load_workflow(WORKFLOW)
    ref_name = upload_image(shot["image"])
    set_input(wf, "LoadImage", "image", ref_name)
    set_input(wf, "WanVideoTextEncode", "positive_prompt", compose_prompt(shot["prompt"], cfg))
    set_input(wf, "WanVideoTextEncode", "negative_prompt", cfg["negative_prompt"])
    set_input(wf, "ImageResizeKJv2", "width", int(cfg["width"]))
    set_input(wf, "ImageResizeKJv2", "height", int(cfg["height"]))
    set_input(wf, "WanVideoImageToVideoEncode", "num_frames", int(shot["num_frames"]))
    set_input(wf, "WanVideoSampler", "seed", int(shot["seed"]), all_nodes=True)
    set_input(wf, "VHS_VideoCombine", "frame_rate", int(cfg["fps"]))
    pid = queue_prompt(wf)
    return first_video_path(wait_for(pid))


def normalize_shot(shot, idx, cfg, base_seed):
    if not isinstance(shot, dict) or "image" not in shot or "prompt" not in shot:
        sys.exit(f"shot {idx}: each shot needs an 'image' (start frame) and a 'prompt'")
    return {
        "image": shot["image"],
        "prompt": shot["prompt"],
        "seed": int(shot.get("seed", base_seed + idx)),
        "num_frames": int(shot.get("num_frames", cfg["num_frames"])),
    }


def build_gallery(serve_dir, clips, cfg):
    cards = [{"src": c["file"],
              "caption": f"<b>{i + 1}</b> · seed {c['seed']} · {c['num_frames']}f @ {cfg['fps']}fps<br>{c['prompt']}"}
             for i, c in enumerate(clips)]
    gallery.write_gallery(serve_dir, f"Video shots — {len(clips)} clips", cards,
                          media="video", theme="dark")


def gpu_vram():
    """Return (free_mb, used_mb, total_mb) from nvidia-smi, or None if unreadable."""
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=memory.free,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            text=True, stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
    free, used, total = (int(x) for x in out.strip().splitlines()[0].split(","))
    return free, used, total


def preflight(force):
    """Loud hardware-safety gate before any WAN render. Bypass with --force."""
    print("\n" + "=" * 72)
    print("  🚩🚩  WAN VIDEO RENDER — HARDWARE RED FLAG  🚩🚩")
    print("=" * 72)
    print("  WAN 14B UNQUANTIZED (bf16 / quantization disabled) HAS CRASHED THIS")
    print("  WHOLE MACHINE: it tries to load ~28 GB/expert onto a 24 GB card -> OOM.")
    print("  WAN cannot share the GPU. Nothing else heavy may be loaded.")
    print("=" * 72)

    vram = gpu_vram()
    if vram is None:
        print("  !! nvidia-smi unreadable — CANNOT verify the GPU is clear. Proceed blind.")
    else:
        free, used, total = vram
        print(f"  VRAM: {used} MB used / {total} MB total  ({free} MB free)")
        if used > GPU_BUSY_THRESHOLD_MB:
            print(f"  ⛔  {used} MB ALREADY IN USE (> {GPU_BUSY_THRESHOLD_MB} MB) — something")
            print("      heavy is co-loaded (Flux / HunyuanVideo / A1111 / another WAN run?).")
            print("      Running WAN now risks a machine crash. Clear the GPU first.")
        else:
            print("  ✓  GPU looks clear.")
    print("=" * 72)

    if force:
        print("  --force given: skipping confirmation. On your head be it.\n")
        return
    reply = input("  Type 'yes' to launch WAN video rendering (anything else aborts): ").strip().lower()
    if reply != "yes":
        sys.exit("  aborted — nothing rendered.")
    print()


def launch_guard():
    """Arm scripts/vram_tripwire.py for this run; SIGKILLs ComfyUI before VRAM/RAM
    exhaustion can freeze the box. Terminated automatically when this driver exits."""
    guard = REPO / "scripts" / "vram_tripwire.py"
    if not guard.exists():
        print("  !! vram_tripwire.py missing — rendering WITHOUT the freeze guard", flush=True)
        return None
    log = open(REPO / "outputs" / "vram_tripwire.log", "a")
    try:
        proc = subprocess.Popen([sys.executable, str(guard), "--match", "main.py --listen"],
                                stdout=log, stderr=subprocess.STDOUT)
    except OSError as exc:
        print(f"  !! could not arm freeze guard: {exc} — rendering unguarded", flush=True)
        return None
    atexit.register(proc.terminate)
    print(f"  ✓ freeze guard armed (pid {proc.pid}) — see outputs/vram_tripwire.log", flush=True)
    return proc


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("shotlist", help="YAML or JSON shot list")
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    ap.add_argument("--force", "--yes", action="store_true",
                    help="skip the preflight VRAM/crash-hazard confirmation")
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.shotlist).read_text())
    cfg = {**VIDEO_DEFAULTS, **{k: v for k, v in spec.items() if k != "shots"}}
    base_seed = int(cfg.pop("seed", int(time.time()) & 0xFFFFFFFF))
    shots = [normalize_shot(s, i, cfg, base_seed) for i, s in enumerate(spec.get("shots", []))]
    if not shots:
        sys.exit("shot list is empty")

    preflight(args.force)
    launch_guard()

    serve_dir = Path(tempfile.mkdtemp(prefix="video_shot_"))
    clips = []
    for i, s in enumerate(shots):
        print(f"[{i+1}/{len(shots)}] {s['prompt'][:70]}  (seed {s['seed']}, {s['num_frames']}f)")
        out = render_shot(s, cfg)
        local = serve_dir / f"shot_{i+1:02d}{out.suffix}"
        shutil.copy(out, local)
        clips.append({"file": local.name, "prompt": s["prompt"],
                      "seed": s["seed"], "num_frames": s["num_frames"]})

    build_gallery(serve_dir, clips, cfg)
    gallery.serve_and_block(serve_dir, keep=args.keep)


if __name__ == "__main__":
    main()
