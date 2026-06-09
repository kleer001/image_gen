#!/usr/bin/env python3
"""FLUX.2 Klein 9B reference-driven image editing (isolated ComfyUI :8189).

Edit / composite from one or more reference images by text instruction — the
open analog to Kontext-style multi-image conditioning. Each reference is encoded
to a latent and chained through ReferenceLatent into the positive/negative
conditioning; the output canvas is sized to the first reference.

Runs on the isolated comfyui_flux2/ instance (the production v0.17 ComfyUI can't
run FLUX.2). Uses the distilled 9B model (4 steps, cfg 1) — no extra download.

Usage:
  scripts/flux2_klein_edit.py "edit instruction" --ref a.png [--ref b.png ...]
       [--seed N] [--steps 4] [--cfg 1.0] [--no-open]
"""
import argparse, time, random, shutil, sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flux2_common import DIFFUSION, ENCODER, VAE, render, fetch, stage_ref, serve, block

STAGE = Path("/tmp/flux2_klein_edit_gallery")


def build_graph(prompt, ref_names, seed, steps, cfg):
    g = {
        "70": {"class_type": "UNETLoader", "inputs": {"unet_name": DIFFUSION, "weight_dtype": "default"}},
        "71": {"class_type": "CLIPLoader", "inputs": {"clip_name": ENCODER, "type": "flux2"}},
        "72": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "74": {"class_type": "CLIPTextEncode", "inputs": {"text": prompt, "clip": ["71", 0]}},
        "82": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["74", 0]}},
        "61": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "73": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
    }
    # Per-reference: LoadImage -> ImageScaleToTotalPixels -> VAEEncode (latent)
    ref_latents = []
    first_scaled = None
    for i, name in enumerate(ref_names):
        ld, sc, enc = f"load{i}", f"scale{i}", f"enc{i}"
        g[ld] = {"class_type": "LoadImage", "inputs": {"image": name}}
        g[sc] = {"class_type": "ImageScaleToTotalPixels",
                 "inputs": {"image": [ld, 0], "upscale_method": "nearest-exact", "megapixels": 1.0, "resolution_steps": 1}}
        g[enc] = {"class_type": "VAEEncode", "inputs": {"pixels": [sc, 0], "vae": ["72", 0]}}
        ref_latents.append(enc)
        if first_scaled is None:
            first_scaled = sc
    # Canvas size from the first reference
    g["99"] = {"class_type": "GetImageSize", "inputs": {"image": [first_scaled, 0]}}
    g["62"] = {"class_type": "Flux2Scheduler", "inputs": {"steps": steps, "width": ["99", 0], "height": ["99", 1]}}
    g["66"] = {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": ["99", 0], "height": ["99", 1], "batch_size": 1}}
    # Chain ReferenceLatent for each reference, onto positive and negative conditioning
    pos, neg = ["74", 0], ["82", 0]
    for i, enc in enumerate(ref_latents):
        rp, rn = f"refpos{i}", f"refneg{i}"
        g[rp] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": pos, "latent": [enc, 0]}}
        g[rn] = {"class_type": "ReferenceLatent", "inputs": {"conditioning": neg, "latent": [enc, 0]}}
        pos, neg = [rp, 0], [rn, 0]
    g["63"] = {"class_type": "CFGGuider", "inputs": {"model": ["70", 0], "positive": pos, "negative": neg, "cfg": cfg}}
    g["64"] = {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["73", 0], "guider": ["63", 0], "sampler": ["61", 0], "sigmas": ["62", 0], "latent_image": ["66", 0]}}
    g["65"] = {"class_type": "VAEDecode", "inputs": {"samples": ["64", 0], "vae": ["72", 0]}}
    g["67"] = {"class_type": "SaveImage", "inputs": {"images": ["65", 0], "filename_prefix": "klein_edit"}}
    return g


def write_gallery(prompt, meta, refs, imgs):
    for r in refs:
        shutil.copyfile(r, STAGE / ("ref_" + Path(r).name))
    ref_cards = "".join(f'<figure><img src="ref_{Path(r).name}"><figcaption>reference</figcaption></figure>' for r in refs)
    out_cards = "".join(f'<figure><img src="{im}"><figcaption>edited</figcaption></figure>' for im in imgs)
    html = f"""<!doctype html><meta charset=utf-8><title>FLUX.2 Klein 9B — edit</title>
<style>body{{background:#fafafa;color:#1a1a1a;font:15px/1.5 system-ui,sans-serif;margin:24px}}
.p{{background:#fff;border:1px solid #ddd;padding:12px 16px;border-radius:8px;max-width:1100px}}
h2{{font-size:15px;margin:20px 0 6px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;max-width:1100px}}
figure{{margin:0;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px}}
img{{width:100%;height:auto;border-radius:4px;display:block}}
figcaption{{margin-top:6px;font-size:12px;color:#666}}</style>
<h1>FLUX.2 Klein 9B — reference edit</h1><div class=p><b>{meta}</b><br>{prompt}</div>
<h2>Reference(s)</h2><div class=grid>{ref_cards}</div>
<h2>Result</h2><div class=grid>{out_cards}</div>"""
    (STAGE / "index.html").write_text(html)


def main():
    ap = argparse.ArgumentParser(description="FLUX.2 Klein 9B reference-driven editing on :8189")
    ap.add_argument("prompt", help="edit instruction")
    ap.add_argument("--ref", action="append", required=True, help="reference image path (repeatable)")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--cfg", type=float, default=1.0)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    ref_names = [stage_ref(r) for r in a.ref]
    print(f"Klein 9B edit | {len(ref_names)} ref(s) | seed {seed} | {a.steps} steps | cfg {a.cfg}")
    t0 = time.time()
    hist = render(build_graph(a.prompt, ref_names, seed, a.steps, a.cfg))
    imgs = fetch(hist, STAGE)
    dt = time.time() - t0
    print(f"done in {dt:.0f}s -> {imgs}")
    write_gallery(a.prompt, f"{len(ref_names)} ref · seed {seed} · {a.steps} steps · cfg {a.cfg} · {dt:.0f}s", a.ref, imgs)
    serve(STAGE, not a.no_open)
    if not a.no_open:
        print("serving; Ctrl-C to stop")
        block()


if __name__ == "__main__":
    main()
