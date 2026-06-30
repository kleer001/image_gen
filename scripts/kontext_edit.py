#!/usr/bin/env python3
"""Multi-reference FLUX.1 Kontext editing on the production stack (:8188).

Composite or edit from one or more reference images by a text instruction. Each
reference is scaled to a Kontext bucket, VAE-encoded, and chained through
ReferenceLatent onto the positive conditioning, so the model conditions on every
reference at once — the in-context multi-image upgrade to single-reference
Kontext. Output canvas is sized to the first reference's bucket.

Runs against the installed Flux.1-Kontext-dev (no new model). Mirrors the
isolated-instance flux2_klein_edit.py, but targets the production v0.17 ComfyUI
and reuses storyboard.py's API client + gallery.py for display.

Usage:
  scripts/kontext_edit.py "edit instruction" --ref a.png [--ref b.png ...]
       [--seed N] [--steps 20] [--guidance 2.5] [--keep] [--no-open]
"""
import argparse
import random
import shutil
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery  # noqa: E402
from storyboard import queue_prompt, wait_for, first_output_path, upload_image  # noqa: E402


def build_graph(prompt, ref_names, seed, steps, guidance):
    """Flux.1 Kontext graph with one ReferenceLatent per reference on positive.

    Generalizes storyboard_panel.json to N references: each reference is encoded
    and chained into the positive conditioning; the first reference's latent is
    the KSampler canvas, so the output adopts its Kontext bucket dimensions.
    """
    g = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": "flux1-kontext-dev.safetensors", "weight_dtype": "fp8_e4m3fn"}},
        "2": {"class_type": "DualCLIPLoader",
              "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp8_e4m3fn.safetensors",
                         "type": "flux", "device": "default"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "7": {"class_type": "CLIPTextEncode", "inputs": {"clip": ["2", 0], "text": prompt}},
        "8": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["7", 0]}},
    }
    encs = []
    for i, name in enumerate(ref_names):
        ld, sc, enc = f"load{i}", f"scale{i}", f"enc{i}"
        g[ld] = {"class_type": "LoadImage", "inputs": {"image": name}}
        g[sc] = {"class_type": "FluxKontextImageScale", "inputs": {"image": [ld, 0]}}
        g[enc] = {"class_type": "VAEEncode", "inputs": {"pixels": [sc, 0], "vae": ["3", 0]}}
        encs.append(enc)
    pos = ["7", 0]
    for i, enc in enumerate(encs):
        rl = f"ref{i}"
        g[rl] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": pos, "latent": [enc, 0]}}
        pos = [rl, 0]
    g["10"] = {"class_type": "FluxGuidance", "inputs": {"conditioning": pos, "guidance": guidance}}
    g["11"] = {"class_type": "KSampler",
               "inputs": {"model": ["1", 0], "positive": ["10", 0], "negative": ["8", 0],
                          "latent_image": [encs[0], 0], "seed": seed, "steps": steps, "cfg": 1,
                          "sampler_name": "euler", "scheduler": "simple", "denoise": 1}}
    g["12"] = {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["3", 0]}}
    g["14"] = {"class_type": "SaveImage", "inputs": {"images": ["12", 0], "filename_prefix": "kontext_edit"}}
    return g


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("prompt", help="edit instruction")
    ap.add_argument("--ref", action="append", required=True, help="reference image path (repeatable)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--steps", type=int, default=20)
    ap.add_argument("--guidance", type=float, default=2.5)
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    ap.add_argument("--no-open", action="store_true", help="write gallery but do not serve/open")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)

    ref_names = [upload_image(Path(r).expanduser()) for r in a.ref]
    print(f"Kontext edit | {len(ref_names)} ref(s) | seed {seed} | {a.steps} steps | guidance {a.guidance}")
    t0 = time.time()
    pid = queue_prompt(build_graph(a.prompt, ref_names, seed, a.steps, a.guidance))
    out = first_output_path(wait_for(pid))
    dt = time.time() - t0
    print(f"done in {dt:.0f}s -> {out}")

    serve_dir = Path(tempfile.mkdtemp(prefix="kontext_edit_"))
    cards = []
    for r in a.ref:
        dst = serve_dir / ("ref_" + Path(r).name)
        shutil.copyfile(Path(r).expanduser(), dst)
        cards.append({"src": dst.name, "caption": "reference"})
    shutil.copyfile(out, serve_dir / out.name)
    cards.append({"src": out.name, "caption": f"<b>edited</b><br>{a.prompt}"})
    gallery.write_gallery(serve_dir, f"FLUX.1 Kontext · {len(ref_names)} ref", cards,
                          media="img", theme="light",
                          subtitle=f"seed {seed} · {a.steps} steps · guidance {a.guidance} · {dt:.0f}s")
    if a.no_open:
        print(f"gallery at {serve_dir}/index.html")
    else:
        gallery.serve_and_block(serve_dir, keep=a.keep)


if __name__ == "__main__":
    main()
