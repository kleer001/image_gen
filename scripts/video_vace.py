#!/usr/bin/env python3
"""VACE reference-to-video driver: shot list -> WAN 2.1 VACE clips -> HTML gallery.

SCAFFOLD. The companion workflow `scaffolds/wan_vace_r2v.json` is UNVALIDATED —
its VACE node schema has not been checked against an installed
ComfyUI-WanVideoWrapper, and the VACE 14B module is not installed yet. See
/TODO.md before relying on this. Once validated, promote the workflow into
workflows/ (so the MCP auto-registers it) and point WORKFLOW_FILE there.

Why this is separate from video_shot.py: WAN 2.2 I2V (video_shot.py) locks
identity only via a single start frame. VACE adds reference-to-video (R2V) —
the open analog to Seedance-style multi-image identity conditioning — so each
shot takes a `reference:` (identity image) plus a motion `prompt:`, and the
character is carried by the reference rather than by an animated first frame.

Usage:
    video_vace.py shots.yaml [--keep]

Shot list format (YAML):

    negative_prompt: "..."            # optional; overrides the default
    num_frames: 81
    fps: 16
    width: 832                        # divisible by 32
    height: 480
    strength: 1.0                     # VACE conditioning strength
    seed: 42                          # base seed; per-shot = base + index
    style_suffix: "..."               # appended to every prompt ("" disables)
    shots:
      - reference: ./refs/zara_sheet.png
        prompt: "she walks toward camera through neon rain, slow push-in"
      - reference: ./refs/zara_sheet.png
        prompt: "close-up, she glances over her shoulder, half-smile"
        strength: 0.8
        seed: 9001
"""
import argparse
import sys
import shutil
import tempfile
import time
from pathlib import Path

import yaml

# Reuse the generic ComfyUI/HTTP + gallery helpers from the video_shot driver.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_shot as vs  # noqa: E402

REPO = vs.REPO
SCAFFOLDS = REPO / "scaffolds"
WORKFLOW_FILE = SCAFFOLDS / "wan_vace_r2v.json"

DEFAULT_STYLE_SUFFIX = vs.DEFAULT_STYLE_SUFFIX

VACE_DEFAULTS = {
    "negative_prompt": vs.VIDEO_DEFAULTS["negative_prompt"],
    "num_frames": 81,
    "fps": 16,
    "width": 832,
    "height": 480,
    "strength": 1.0,
    "style_suffix": DEFAULT_STYLE_SUFFIX,
}


def load_workflow():
    import json
    wf = json.loads(WORKFLOW_FILE.read_text())
    # Drop scaffold metadata keys (anything that isn't a real node) so the
    # graph queues cleanly — ComfyUI rejects entries without a class_type.
    return {k: v for k, v in wf.items()
            if isinstance(v, dict) and "class_type" in v}


def render_shot(shot, cfg):
    wf = load_workflow()
    ref_name = vs.upload_image(shot["reference"])
    vs.set_input(wf, "LoadImage", "image", ref_name)
    vs.set_input(wf, "WanVideoTextEncode", "positive_prompt", vs.compose_prompt(shot["prompt"], cfg))
    vs.set_input(wf, "WanVideoTextEncode", "negative_prompt", cfg["negative_prompt"])
    vs.set_input(wf, "ImageResizeKJv2", "width", int(cfg["width"]))
    vs.set_input(wf, "ImageResizeKJv2", "height", int(cfg["height"]))
    vs.set_input(wf, "WanVideoVACEEncode", "num_frames", int(shot["num_frames"]))
    vs.set_input(wf, "WanVideoVACEEncode", "strength", float(shot["strength"]))
    vs.set_input(wf, "WanVideoSampler", "seed", int(shot["seed"]), all_nodes=True)
    vs.set_input(wf, "VHS_VideoCombine", "frame_rate", int(cfg["fps"]))
    pid = vs.queue_prompt(wf)
    return vs.first_video_path(vs.wait_for(pid))


def normalize_shot(shot, idx, cfg, base_seed):
    if not isinstance(shot, dict) or "reference" not in shot or "prompt" not in shot:
        sys.exit(f"shot {idx}: each shot needs a 'reference' (identity image) and a 'prompt'")
    return {
        "reference": shot["reference"],
        "prompt": shot["prompt"],
        "seed": int(shot.get("seed", base_seed + idx)),
        "num_frames": int(shot.get("num_frames", cfg["num_frames"])),
        "strength": float(shot.get("strength", cfg["strength"])),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("shotlist", help="YAML or JSON shot list")
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    args = ap.parse_args()

    if not WORKFLOW_FILE.exists():
        sys.exit(f"missing workflow scaffold: {WORKFLOW_FILE}")

    spec = yaml.safe_load(Path(args.shotlist).read_text())
    cfg = {**VACE_DEFAULTS, **{k: v for k, v in spec.items() if k != "shots"}}
    base_seed = int(cfg.pop("seed", int(time.time()) & 0xFFFFFFFF))
    shots = [normalize_shot(s, i, cfg, base_seed) for i, s in enumerate(spec.get("shots", []))]
    if not shots:
        sys.exit("shot list is empty")

    serve_dir = Path(tempfile.mkdtemp(prefix="video_vace_"))
    clips = []
    for i, s in enumerate(shots):
        print(f"[{i+1}/{len(shots)}] {s['prompt'][:70]}  (seed {s['seed']}, {s['num_frames']}f, str {s['strength']})")
        out = render_shot(s, cfg)
        local = serve_dir / f"shot_{i+1:02d}{out.suffix}"
        shutil.copy(out, local)
        clips.append({"file": local.name, "prompt": s["prompt"],
                      "seed": s["seed"], "num_frames": s["num_frames"]})

    vs.build_gallery(serve_dir, clips, cfg)
    port = vs.free_port()
    vs.serve(str(serve_dir), port)
    url = f"http://localhost:{port}/index.html"
    opened = vs.open_in_browser(url)
    print(f"\n  Gallery: {url}" + ("" if opened else "  (open it manually)"))
    print("  Ctrl-C to stop the server." + ("" if args.keep else f"  Temp dir {serve_dir} removed on exit."))
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        if not args.keep:
            shutil.rmtree(serve_dir, ignore_errors=True)
        print("\n  stopped.")


if __name__ == "__main__":
    main()
