#!/usr/bin/env python3
"""FLUX.2 Klein 9B text-to-image engine (isolated ComfyUI on :8189).

A first-class Klein image driver, analogous to storyboard.py/video_shot.py: it
hits the isolated comfyui_flux2/ instance (the production v0.17 ComfyUI can't run
FLUX.2), renders one prompt, and opens a browser gallery. Distilled 9B defaults
(4 steps, cfg 1, euler); bump --steps for the base model.

Usage:
  scripts/flux2_klein.py "a prompt" [--steps 4] [--seed N] [--width 1024]
                         [--height 1024] [--cfg 1.0] [--negative "..."]
                         [--batch 1] [--no-open]
"""
import argparse, time, random, shutil, sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flux2_common import DIFFUSION, ENCODER, VAE, render, fetch, serve, block

STAGE = Path("/tmp/flux2_klein_gallery")


def build_graph(prompt, negative, seed, steps, width, height, cfg, batch):
    return {
        "10": {"class_type": "UNETLoader", "inputs": {"unet_name": DIFFUSION, "weight_dtype": "default"}},
        "11": {"class_type": "CLIPLoader", "inputs": {"clip_name": ENCODER, "type": "flux2"}},
        "12": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "13": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["11", 0]}},
        "14": {"class_type": "CLIPTextEncode", "inputs": {"text": negative, "clip": ["11", 0]}},
        "15": {"class_type": "CFGGuider", "inputs": {"model": ["10", 0], "positive": ["13", 0], "negative": ["14", 0], "cfg": cfg}},
        "16": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "17": {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": width, "height": height}},
        "18": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "19": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": width, "height": height, "batch_size": batch}},
        "20": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["18", 0], "guider": ["15", 0],
               "sampler": ["16", 0], "sigmas": ["17", 0], "latent_image": ["19", 0]}},
        "21": {"class_type": "VAEDecode", "inputs": {"samples": ["20", 0], "vae": ["12", 0]}},
        "22": {"class_type": "SaveImage", "inputs": {"images": ["21", 0], "filename_prefix": "klein_t2i"}},
    }


def write_gallery(prompt, meta, imgs):
    cards = "".join(f'<figure><img src="{im}"><figcaption>{im}</figcaption></figure>' for im in imgs)
    html = f"""<!doctype html><meta charset=utf-8><title>FLUX.2 Klein 9B</title>
<style>body{{background:#fafafa;color:#1a1a1a;font:15px/1.5 system-ui,sans-serif;margin:24px}}
.p{{background:#fff;border:1px solid #ddd;padding:12px 16px;border-radius:8px;max-width:1100px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(360px,1fr));gap:20px;margin-top:20px;max-width:1100px}}
figure{{margin:0;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px}}
img{{width:100%;height:auto;border-radius:4px;display:block}}
figcaption{{margin-top:8px;font-size:12px;color:#666}}</style>
<h1>FLUX.2 Klein 9B</h1><div class=p><b>{meta}</b><br>{prompt}</div>
<div class=grid>{cards}</div>"""
    (STAGE / "index.html").write_text(html)


def main():
    ap = argparse.ArgumentParser(description="FLUX.2 Klein 9B t2i on the isolated :8189 instance")
    ap.add_argument("prompt")
    ap.add_argument("--negative", default="")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--width", type=int, default=1024)
    ap.add_argument("--height", type=int, default=1024)
    ap.add_argument("--cfg", type=float, default=1.0)
    ap.add_argument("--batch", type=int, default=1)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    print(f"Klein 9B | seed {seed} | {a.steps} steps | {a.width}x{a.height} | cfg {a.cfg}")
    t0 = time.time()
    hist = render(build_graph(a.prompt, a.negative, seed, a.steps, a.width, a.height, a.cfg, a.batch))
    imgs = fetch(hist, STAGE)
    dt = time.time() - t0
    print(f"done in {dt:.0f}s -> {imgs}")
    write_gallery(a.prompt, f"seed {seed} · {a.steps} steps · cfg {a.cfg} · {a.width}x{a.height} · {dt:.0f}s", imgs)
    serve(STAGE, not a.no_open)
    if not a.no_open:
        print("serving; Ctrl-C to stop")
        block()


if __name__ == "__main__":
    main()
