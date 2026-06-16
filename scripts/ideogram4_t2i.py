#!/usr/bin/env python3
"""Ideogram 4 (nf4) text-to-image driver — isolated diffusers env, NOT ComfyUI.

Loads the local nf4 diffusers repo (models/ideogram-4-nf4) via Ideogram4Pipeline
(bitsandbytes nf4 is baked into the component configs) and renders either a plain
text prompt or a structured JSON caption, then opens an HTML gallery.

JSON caption schema (pass with @file.json): top-level high_level_description +
style_description + compositional_deconstruction{background, elements:[...]}.
Each element is {type:"obj"|"text", bbox:[y_min,x_min,y_max,x_max] in 0-1000
top-left coords, desc, text(for type=text)}. The placed bbox doubles as the
ground-truth location (the Where's-Waldo answer key).

Run with the dedicated venv (nf4 needs bitsandbytes; fp8 build would not run on
this sm_86 card):
    ideogram4_env/.venv/bin/python scripts/ideogram4_t2i.py "a prompt" [opts]
    ideogram4_env/.venv/bin/python scripts/ideogram4_t2i.py @scene.json --width 1536 --height 1024
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

import torch
from diffusers import Ideogram4Pipeline

REPO = Path("/media/menser/fauna/image_gen")
# The diffusers-loadable build (separate to_q/k/v). The plain ideogram-4-nf4 repo
# uses fused qkv for the ideogram-oss CLI and will NOT load via Ideogram4Pipeline.
MODEL = REPO / "models" / "ideogram-4-nf4-diffusers"

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prompt", help="plain text prompt, or @path.json for a JSON caption")
    ap.add_argument("--steps", type=int, default=48, help="sampling steps; 48 uses the native CFG schedule, other counts use a constant --guidance")
    ap.add_argument("--guidance", type=float, default=None, help="constant CFG scale (overrides the native per-step schedule); auto-applied when --steps != 48")
    ap.add_argument("--width", type=int, default=1024, help="multiple of 16, 256-2048")
    ap.add_argument("--height", type=int, default=1024, help="multiple of 16, 256-2048")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    args = ap.parse_args()

    prompt = args.prompt
    if prompt.startswith("@"):
        prompt = json.dumps(json.loads(Path(prompt[1:]).read_text()))

    print("loading Ideogram4Pipeline (nf4)...", flush=True)
    # bnb-quantized weights must be placed on-device during load (device_map), not
    # moved with .to() afterward (that raises a meta-tensor copy error).
    pipe = Ideogram4Pipeline.from_pretrained(str(MODEL), torch_dtype=torch.bfloat16, device_map="cuda")

    # The native guidance_schedule is length-48; for any other step count (or an
    # explicit --guidance) use a constant guidance_scale with guidance_schedule=None.
    kwargs = dict(height=args.height, width=args.width, num_inference_steps=args.steps,
                  generator=torch.Generator("cuda").manual_seed(args.seed))
    if args.guidance is not None:
        kwargs.update(guidance_scale=args.guidance, guidance_schedule=None)
    elif args.steps != 48:
        kwargs.update(guidance_scale=5.0, guidance_schedule=None)

    print(f"generating {args.width}x{args.height}, {args.steps} steps...", flush=True)
    img = pipe(prompt, **kwargs).images[0]

    serve_dir = Path(tempfile.mkdtemp(prefix="ideogram4_"))
    img.save(serve_dir / "out_01.png")
    gallery.write_gallery(serve_dir, "Ideogram 4 (nf4)",
                          [{"src": "out_01.png", "caption": args.prompt[:200]}],
                          media="img", theme="light")
    gallery.serve_and_block(serve_dir, keep=args.keep)


if __name__ == "__main__":
    main()
