#!/usr/bin/env python3
"""Render a set of MiniMax H3 variants against one fixed prompt/seed, one gallery.

A comparison harness: every variant shares the base prompt, seed and canvas, so
the only thing that differs between clips is what the variant declares — a LoRA
stack, an `embedding:` prefix, a step count. One heavy GPU job at a time, so
variants render strictly in sequence.

Variant file (YAML):

    title: LoRA bake-off
    prompt: a base prompt shared by every variant
    seconds: 5
    width: 608
    height: 352
    seed: 7
    steps: 4
    base_loras:                     # applied to every variant that has no `loras`
      - [minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors, 1.0]
    variants:
      - label: baseline
      - label: realism
        prompt: r34l1sm, a base prompt ...      # overrides the shared prompt
        loras:                                  # replaces base_loras entirely
          - [minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors, 1.0]
          - [h3_realism_people_fal.safetensors, 1.0]
        steps: 8                                # overrides the shared step count

Usage:
  scripts/h3_batch.py variants.yaml [--keep] [--no-open]
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
from h3_t2v import FPS, TURBO_LORA, align_length, build_graph, fetch_video, submit, wait_for


def render_variant(variant, cfg, stage, index):
    prompt = variant.get("prompt") or cfg.get("prompt")
    if prompt is None:
        raise KeyError(f"variant {variant['label']!r} has no prompt and the file "
                       "sets no shared `prompt:`")
    loras = [tuple(x) for x in variant.get("loras", cfg["base_loras"])]
    steps = int(variant.get("steps", cfg["steps"]))
    width = int(variant.get("width", cfg["width"]))
    height = int(variant.get("height", cfg["height"]))
    length = align_length(variant.get("seconds", cfg["seconds"]))

    print(f"  [{index}] {variant['label']}: {steps} steps, {width}x{height}, "
          f"{len(loras)} lora(s) ... ", end="", flush=True)
    t0 = time.time()
    sampler = variant.get("sampler", cfg["sampler"])
    scheduler = variant.get("scheduler", cfg["scheduler"])
    latent_scale = variant.get("latent_scale", cfg.get("latent_scale"))
    graph = build_graph(prompt, cfg["seed"], steps, width, height, length, loras,
                        sampler, scheduler, latent_scale)
    hist = wait_for(submit(graph), cfg["timeout"])
    clip = fetch_video(hist, stage)
    dt = time.time() - t0
    # SaveVideo numbers its own files, so each variant lands under its own name.
    named = f"{index:02d}_{variant['label'].replace(' ', '_')}.mp4"
    (Path(stage) / clip).rename(Path(stage) / named)
    print(f"{dt:.0f}s")
    return {"label": variant["label"], "file": named, "seconds": dt, "steps": steps,
            "loras": loras, "prompt": prompt, "dims": f"{width}x{height}", "length": length,
            "recipe": f"{sampler} + {scheduler}"
                      + (f" · latent x{latent_scale}" if latent_scale is not None else "")}


def main():
    ap = argparse.ArgumentParser(description="MiniMax H3 variant bake-off on :8191")
    ap.add_argument("variants", help="YAML variant file")
    ap.add_argument("--keep", action="store_true")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    cfg = yaml.safe_load(Path(a.variants).read_text())
    cfg.setdefault("seconds", 5)
    cfg.setdefault("width", 608)
    cfg.setdefault("height", 352)
    cfg.setdefault("seed", 7)
    cfg.setdefault("steps", 4)
    cfg.setdefault("timeout", 3600)
    cfg.setdefault("base_loras", [[TURBO_LORA, 1.0]])
    cfg.setdefault("sampler", "res_multistep")
    cfg.setdefault("scheduler", "simple")

    stage = Path(tempfile.mkdtemp(prefix="h3_batch_"))
    length = align_length(cfg["seconds"])
    print(f"{cfg['title']} — {len(cfg['variants'])} variants | {cfg['width']}x{cfg['height']} | "
          f"{length}f @ {FPS}fps | seed {cfg['seed']}")

    results = [render_variant(v, cfg, stage, i) for i, v in enumerate(cfg["variants"], 1)]

    cards = []
    for r in results:
        stack = "<br>".join(f"{Path(n).stem} @ {s}" for n, s in r["loras"]) or "no LoRA"
        cards.append({"src": r["file"],
                      "caption": f"<b>{r['label']}</b> · {r['dims']} · {r['length']}f · "
                                 f"{r['steps']} steps · {r['recipe']} · {r['seconds']:.0f}s<br>"
                                 f"<small>{stack}</small><br><small>{r['prompt']}</small>"})
    total = sum(r["seconds"] for r in results)
    gallery.write_gallery(
        stage, cfg["title"], cards, media="video", theme="dark", muted=False,
        subtitle=f"{cfg['width']}x{cfg['height']} · {length}f @ {FPS}fps · seed {cfg['seed']} "
                 f"· {total / 60:.1f} min total",
        footer="Unmute — H3 generates the soundtrack in the same pass as the video.")
    if a.no_open:
        print(f"gallery dir: {stage}")
        return
    gallery.serve_and_block(stage, keep=a.keep)


if __name__ == "__main__":
    main()
