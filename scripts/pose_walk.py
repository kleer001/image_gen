#!/usr/bin/env python3
"""Pose-walk driver: shot list -> DWPose -> ControlNet -> AnimateDiff clips -> HTML gallery.

SCAFFOLD. The companion workflow `scaffolds/dwpose_walk_animatediff.json` is
UNVALIDATED — its DWPose / IPAdapter / VHS node schemas have not been checked
against installed custom nodes, and the SD1.5 + ControlNet + IPAdapter weights
are not installed yet. See /TODO.md before relying on this. Once validated,
promote the workflow into workflows/ (so the MCP auto-registers it) and point
WORKFLOW_FILE there.

What it does (Option 1 of the DWPose->ControlNet design): for each shot it takes
a *driving walk video* and a *character identity image*. DWPose extracts the
skeleton sequence from the driving video, an OpenPose ControlNet drives the limbs
per frame, AnimateDiff's motion module keeps the frames temporally coherent, and
an IPAdapter carries the character's identity across the clip. The driving video
supplies the gait; the reference image + prompt supply *who* is walking.

Why this is separate from video_shot.py: WAN I2V locks identity via a single
start frame and has no pose control. This pipeline is pose-driven (skeleton from
a driving clip) and light enough to run on a 24GB card with no hardware red-flag.

Usage:
    pose_walk.py shots.yaml [--keep]

Shot list format (YAML):

    reference: ./refs/zara.png        # global identity image (IPAdapter); per-shot override allowed
    negative_prompt: "..."            # optional; overrides the default
    fps: 8                            # output playback / VHS frame_rate
    sample_fps: 8                     # driving-video resample rate (VHS force_rate)
    width: 512                        # render dims (SD1.5 sweet spot ~512-768)
    height: 768
    num_frames: 16                    # frames per clip; also the latent batch size
    select_every_nth: 1              # subsample the driving video
    steps: 20
    cfg: 7.0
    ipadapter_weight: 0.8            # identity strength (0.6 looser .. 1.0 tighter)
    controlnet_strength: 1.0         # pose adherence
    seed: 42                          # base seed; per-shot = base + index
    style_suffix: "..."               # appended to every prompt ("" disables)
    shots:
      - video: ./drive/walk_loop.mp4
        prompt: "a young woman in a red jacket and jeans, full body, walking"
      - video: ./drive/walk_loop.mp4
        prompt: "an old man with a cane, full body, walking slowly"
        reference: ./refs/grandpa.png   # per-shot identity override
        seed: 9001
        ipadapter_weight: 0.9

The driving video must have at least num_frames * select_every_nth frames after
skip_first_frames, or VHS produces fewer frames than the latent batch expects.
"""
import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

import yaml

# Reuse the generic ComfyUI/HTTP + gallery helpers from the video_shot driver.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_shot as vs  # noqa: E402

REPO = vs.REPO
SCAFFOLDS = REPO / "scaffolds"
COMFY_INPUT = REPO / "comfyui" / "input"
WORKFLOW_FILE = SCAFFOLDS / "dwpose_walk_animatediff.json"

# Tailored to character animation, not cinematic plates: keep the figure whole
# and the scene clean so the pose reads and identity stays stable frame-to-frame.
DEFAULT_STYLE_SUFFIX = (
    "full-body shot, consistent character design, simple uncluttered background, "
    "even lighting, smooth natural motion, no flicker"
)

POSE_DEFAULTS = {
    "negative_prompt": (
        "ugly, deformed, extra limbs, missing limbs, fused fingers, blurry, "
        "watermark, text, low quality, flicker, jittery"
    ),
    "fps": 8,
    "sample_fps": 8,
    "width": 512,
    "height": 768,
    "num_frames": 16,
    "select_every_nth": 1,
    "steps": 20,
    "cfg": 7.0,
    "ipadapter_weight": 0.8,
    "controlnet_strength": 1.0,
    "style_suffix": DEFAULT_STYLE_SUFFIX,
}


def load_workflow():
    wf = json.loads(WORKFLOW_FILE.read_text())
    # Drop scaffold metadata keys (anything that isn't a real node) so the graph
    # queues cleanly — ComfyUI rejects top-level entries without a class_type.
    return {k: v for k, v in wf.items()
            if isinstance(v, dict) and "class_type" in v}


def stage_video(src):
    """Copy a driving clip into ComfyUI's input dir so VHS_LoadVideo can read it."""
    src = Path(src).expanduser()
    if not src.exists():
        sys.exit(f"driving video not found: {src}")
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(src, COMFY_INPUT / src.name)
    return src.name


def set_text_by_title(wf, title, text):
    """Target one of the two CLIPTextEncode nodes by its _meta title."""
    for node in wf.values():
        if node.get("_meta", {}).get("title") == title:
            node["inputs"]["text"] = text
            return
    raise KeyError(f"workflow has no node titled {title!r}")


def render_shot(shot, cfg):
    wf = load_workflow()

    video_name = stage_video(shot["video"])
    ref_name = vs.upload_image(shot["reference"])

    # Driving clip -> DWPose
    vs.set_input(wf, "VHS_LoadVideo", "video", video_name)
    vs.set_input(wf, "VHS_LoadVideo", "frame_load_cap", int(shot["num_frames"]))
    vs.set_input(wf, "VHS_LoadVideo", "select_every_nth", int(cfg["select_every_nth"]))
    vs.set_input(wf, "VHS_LoadVideo", "force_rate", int(cfg["sample_fps"]))

    # Identity image -> IPAdapter
    vs.set_input(wf, "LoadImage", "image", ref_name)
    vs.set_input(wf, "IPAdapter", "weight", float(shot["ipadapter_weight"]))

    # Prompts (two CLIPTextEncode nodes, disambiguated by title)
    set_text_by_title(wf, "Positive Prompt", vs.compose_prompt(shot["prompt"], cfg))
    set_text_by_title(wf, "Negative Prompt", cfg["negative_prompt"])

    # Pose adherence + render
    vs.set_input(wf, "ControlNetApplyAdvanced", "strength", float(shot["controlnet_strength"]))
    vs.set_input(wf, "EmptyLatentImage", "width", int(cfg["width"]))
    vs.set_input(wf, "EmptyLatentImage", "height", int(cfg["height"]))
    # Latent batch must match the DWPose frame count VHS produces.
    vs.set_input(wf, "EmptyLatentImage", "batch_size", int(shot["num_frames"]))
    vs.set_input(wf, "KSampler", "seed", int(shot["seed"]))
    vs.set_input(wf, "KSampler", "steps", int(cfg["steps"]))
    vs.set_input(wf, "KSampler", "cfg", float(cfg["cfg"]))
    vs.set_input(wf, "VHS_VideoCombine", "frame_rate", int(cfg["fps"]))

    pid = vs.queue_prompt(wf)
    return vs.first_video_path(vs.wait_for(pid))


def normalize_shot(shot, idx, cfg, base_seed):
    if not isinstance(shot, dict) or "video" not in shot or "prompt" not in shot:
        sys.exit(f"shot {idx}: each shot needs a 'video' (driving walk clip) and a 'prompt'")
    reference = shot.get("reference", cfg.get("reference"))
    if not reference:
        sys.exit(f"shot {idx}: no 'reference' identity image (set one globally or per-shot)")
    return {
        "video": shot["video"],
        "prompt": shot["prompt"],
        "reference": reference,
        "seed": int(shot.get("seed", base_seed + idx)),
        "num_frames": int(shot.get("num_frames", cfg["num_frames"])),
        "ipadapter_weight": float(shot.get("ipadapter_weight", cfg["ipadapter_weight"])),
        "controlnet_strength": float(shot.get("controlnet_strength", cfg["controlnet_strength"])),
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("shotlist", help="YAML or JSON shot list")
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    args = ap.parse_args()

    if not WORKFLOW_FILE.exists():
        sys.exit(f"missing workflow scaffold: {WORKFLOW_FILE}")

    spec = yaml.safe_load(Path(args.shotlist).read_text())
    cfg = {**POSE_DEFAULTS, **{k: v for k, v in spec.items() if k != "shots"}}
    base_seed = int(cfg.pop("seed", int(time.time()) & 0xFFFFFFFF))
    shots = [normalize_shot(s, i, cfg, base_seed) for i, s in enumerate(spec.get("shots", []))]
    if not shots:
        sys.exit("shot list is empty")

    serve_dir = Path(tempfile.mkdtemp(prefix="pose_walk_"))
    clips = []
    for i, s in enumerate(shots):
        print(f"[{i+1}/{len(shots)}] {s['prompt'][:70]}  (seed {s['seed']}, {s['num_frames']}f)")
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
