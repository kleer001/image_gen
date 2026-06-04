#!/usr/bin/env python3
"""Video post chain: ESRGAN frame upscale + RIFE interpolation -> HTML gallery.

SCAFFOLD. The companion workflow `scaffolds/video_post_upscale_interp.json` is
UNVALIDATED and RIFE needs the ComfyUI-Frame-Interpolation custom node, which is
NOT part of the base stack. See /TODO.md before relying on this. Once validated,
promote the workflow into workflows/ and point WORKFLOW_FILE there.

The OSS substitute for Topaz Video AI: takes the clips out of video_shot.py /
video_vace.py (720p-class, 16 fps) and (1) upscales each frame with an installed
ESRGAN model, (2) downscales to a clean target, (3) interpolates with RIFE to
multiply the frame rate for temporal smoothness. Order follows the chain
documented in CLAUDE.md (upscale -> interpolate); see /TODO.md for the VRAM
tradeoff of swapping the two.

Usage:
    video_post.py clip1.mp4 [clip2.mp4 ...] [options]

Options:
    --fps N            source fps of the input clips (default 16)
    --multiplier N     RIFE frame multiplier; output fps = fps * N (default 2)
    --width / --height target dims after the 4x upscale (default 1664x960 = 2x
                       of an 832x480 render, aspect-preserving)
    --upscale-model    ESRGAN model in models/upscale_models (default 4x-UltraSharp.pth)
    --rife-ckpt        RIFE checkpoint (default rife47.pth)
    --keep             keep the gallery temp dir after exit
"""
import argparse
import json
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import video_shot as vs  # noqa: E402

REPO = vs.REPO
SCAFFOLDS = REPO / "scaffolds"
COMFY_INPUT = REPO / "comfyui" / "input"
WORKFLOW_FILE = SCAFFOLDS / "video_post_upscale_interp.json"


def load_workflow():
    wf = json.loads(WORKFLOW_FILE.read_text())
    # Drop scaffold metadata keys (anything without a class_type) before queueing.
    return {k: v for k, v in wf.items()
            if isinstance(v, dict) and "class_type" in v}


def stage_input(src):
    """Copy an input clip into ComfyUI's input dir so VHS_LoadVideo can read it."""
    src = Path(src).expanduser()
    if not src.exists():
        sys.exit(f"input not found: {src}")
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    dst = COMFY_INPUT / src.name
    shutil.copy(src, dst)
    return src.name


def run_post(src, cfg):
    wf = load_workflow()
    name = stage_input(src)
    vs.set_input(wf, "VHS_LoadVideo", "video", name)
    vs.set_input(wf, "UpscaleModelLoader", "model_name", cfg["upscale_model"])
    vs.set_input(wf, "ImageScale", "width", int(cfg["width"]))
    vs.set_input(wf, "ImageScale", "height", int(cfg["height"]))
    vs.set_input(wf, "RIFE VFI", "multiplier", int(cfg["multiplier"]))
    vs.set_input(wf, "RIFE VFI", "ckpt_name", cfg["rife_ckpt"])
    vs.set_input(wf, "VHS_VideoCombine", "frame_rate", int(cfg["fps"]) * int(cfg["multiplier"]))
    pid = vs.queue_prompt(wf)
    return vs.first_video_path(vs.wait_for(pid))


def build_gallery(serve_dir, clips, cfg):
    out_fps = int(cfg["fps"]) * int(cfg["multiplier"])
    cards = []
    for i, c in enumerate(clips):
        cards.append(f"""
      <figure>
        <video src="{c['file']}" controls loop muted playsinline preload="metadata"></video>
        <figcaption><b>{i+1}</b> · {c['src']}<br>{cfg['width']}x{cfg['height']} · {out_fps}fps (x{cfg['multiplier']} RIFE) · {cfg['upscale_model']}</figcaption>
      </figure>""")
    html = f"""<!doctype html><html><head><meta charset="utf-8"><title>Post chain</title>
<style>
  body {{ background:#0f0f12; color:#eee; font:13px/1.4 -apple-system,system-ui,sans-serif; max-width:1200px; margin:2em auto; padding:0 1em; }}
  .grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(360px,1fr)); gap:1em; }}
  figure {{ margin:0; background:#1a1a1f; border:1px solid #333; border-radius:6px; overflow:hidden; }}
  video {{ width:100%; display:block; background:#000; }}
  figcaption {{ padding:.6em .8em; color:#bbb; }}
</style></head><body>
  <h2>Post chain — {len(clips)} clips (upscale + RIFE)</h2>
  <div class="grid">{''.join(cards)}</div>
</body></html>"""
    (serve_dir / "index.html").write_text(html)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("inputs", nargs="+", help="input video clip(s)")
    ap.add_argument("--fps", type=int, default=16, help="source fps of input clips")
    ap.add_argument("--multiplier", type=int, default=2, help="RIFE frame multiplier")
    ap.add_argument("--width", type=int, default=1664, help="target width after upscale")
    ap.add_argument("--height", type=int, default=960, help="target height after upscale")
    ap.add_argument("--upscale-model", default="4x-UltraSharp.pth")
    ap.add_argument("--rife-ckpt", default="rife47.pth")
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    args = ap.parse_args()

    if not WORKFLOW_FILE.exists():
        sys.exit(f"missing workflow scaffold: {WORKFLOW_FILE}")

    cfg = {
        "fps": args.fps, "multiplier": args.multiplier,
        "width": args.width, "height": args.height,
        "upscale_model": args.upscale_model, "rife_ckpt": args.rife_ckpt,
    }

    serve_dir = Path(tempfile.mkdtemp(prefix="video_post_"))
    clips = []
    for i, src in enumerate(args.inputs):
        print(f"[{i+1}/{len(args.inputs)}] {src} -> {cfg['width']}x{cfg['height']} @ x{cfg['multiplier']}")
        out = run_post(src, cfg)
        local = serve_dir / f"post_{i+1:02d}{out.suffix}"
        shutil.copy(out, local)
        clips.append({"file": local.name, "src": Path(src).name})

    build_gallery(serve_dir, clips, cfg)
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
