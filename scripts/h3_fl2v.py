#!/usr/bin/env python3
"""MiniMax H3 first/last-frame-to-video (+ native audio) on :8191.

The fl2va checkpoint pins keyframe images at frame 0 and at the last frame.
The pinned latents are re-injected at every sampling step, so the clip starts
and ends on those exact images. Give the same image as `first_frame` and
`last_frame` to get a clip that loops: when it plays on repeat, drop its last
frame, because that frame is a copy of the first.

fl2va has no reference input — the subject comes only from the keyframes and
the prompt. So the prompt should describe the subject in words, and refer to
it as "the first frame", not as <Picture 1>.

Usage:
  scripts/h3_fl2v.py shots.yaml [--keep] [--no-open]

Shot file (YAML):

    title: Loop harness
    seconds: 4.45
    width: 768
    height: 768
    seed: 1
    steps: 4
    first_frame: refs/subject.png
    last_frame: refs/subject.png     # optional; same image as first_frame for a loop
    shots:
      - label: idle loop
        prompt: The character from the first frame ...
"""
import argparse
import os
import sys
import tempfile
import time
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gallery
from h3_ref2v import upload_image
from h3_t2v import FPS, align_length, build_graph, fetch_video, submit, wait_for


def main():
    ap = argparse.ArgumentParser(description="MiniMax H3 first/last-frame-to-video on :8191")
    ap.add_argument("shots", help="YAML shot file")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    cfg = yaml.safe_load(Path(a.shots).read_text())
    cfg.setdefault("seconds", 5)
    cfg.setdefault("width", 608)
    cfg.setdefault("height", 352)
    cfg.setdefault("seed", 7)
    cfg.setdefault("steps", 4)
    cfg.setdefault("timeout", 3600)

    length = align_length(cfg["seconds"])
    stage = Path(tempfile.mkdtemp(prefix="h3_fl2v_"))
    keyframes = {k: cfg[k] for k in ("first_frame", "last_frame") if k in cfg}
    uploaded = {k: upload_image(p) for k, p in keyframes.items()}

    print(f"{cfg['title']} — {len(cfg['shots'])} shots | {cfg['width']}x{cfg['height']} | "
          f"{length}f @ {FPS}fps | seed {cfg['seed']}")
    for k, p in keyframes.items():
        print(f"  {k} = {p}")

    results = []
    for i, shot in enumerate(cfg["shots"], 1):
        print(f"  [{i}] {shot['label']} ... ", end="", flush=True)
        t0 = time.time()
        graph = build_graph(shot["prompt"], cfg["seed"], cfg["steps"],
                            cfg["width"], cfg["height"], length)
        graph["15"]["inputs"]["filename_prefix"] = "video/h3_fl2v"
        for k, name in uploaded.items():
            graph[k] = {"class_type": "LoadImage", "inputs": {"image": name}}
            graph["6"]["inputs"][k] = [k, 0]
        clip = fetch_video(wait_for(submit(graph), cfg["timeout"]), stage)
        named = f"{i:02d}_{shot['label'].replace(' ', '_')}.mp4"
        (stage / clip).rename(stage / named)
        dt = time.time() - t0
        print(f"{dt:.0f}s")
        results.append({"label": shot["label"], "file": named,
                        "prompt": shot["prompt"], "seconds": dt})

    # Keyframe stills sit at the top of the page so the pinned frames are judgeable.
    strip = []
    for k, p in keyframes.items():
        (stage / f"{k}.png").write_bytes(Path(p).read_bytes())
        strip.append(f'<figure><img src="{k}.png" style="max-width:260px">'
                     f"<figcaption>{k}<br><small>{Path(p).name}</small></figcaption></figure>")

    cards = [{"src": r["file"],
              "caption": f"<b>{r['label']}</b> · {r['seconds']:.0f}s<br><small>{r['prompt']}</small>"}
             for r in results]
    gallery.write_gallery(
        stage, cfg["title"], cards, media="video", theme="dark", muted=False,
        subtitle=f'<div class="grid">{"".join(strip)}</div>',
        footer="Unmute — H3 generates the soundtrack in the same pass as the video.")
    if a.no_open:
        print(f"gallery dir: {stage}")
        return
    gallery.serve_and_block(stage, keep=a.keep)


if __name__ == "__main__":
    main()
