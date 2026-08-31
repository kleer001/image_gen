#!/usr/bin/env python3
"""TEST: FLUX.2 Klein 4B-base + 4-walk pixel-spritesheet LoRA (isolated :8189).

Replicates the LoRA author's reference workflow exactly: edit a single character
image into a 4x4 walk spritesheet. Settings lifted from the workflow's subgraph
(4B base, qwen_3_4b encoder, LoraLoaderModelOnly @1.0, 512x512, Flux2Scheduler
20 steps, CFGGuider cfg 5, euler; reference encoded + ReferenceLatent on pos/neg).

Usage: flux2_spritesheet_test.py --ref char.png [--seed N] [--no-open]
"""
import argparse, time, random, shutil, sys, os
from pathlib import Path
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flux2_common import render, fetch, stage_ref, serve, block

GRID = 4  # 4x4 sheet


def kcentroid_downscale(image, out_w, out_h, centroids=2):
    """Astropulse k-centroid downscale: per output pixel, quantize its source tile
    to `centroids` colors and keep the dominant one. Preserves crisp pixel edges
    where bilinear/area averaging would smear them."""
    image = image.convert("RGB")
    in_w, in_h = image.size
    wf, hf = in_w / out_w, in_h / out_h
    out = Image.new("RGB", (out_w, out_h))
    px = out.load()
    for x in range(out_w):
        for y in range(out_h):
            tile = image.crop((int(x * wf), int(y * hf), int((x + 1) * wf), int((y + 1) * hf)))
            q = tile.quantize(colors=centroids, method=1, kmeans=centroids, dither=0)
            idx = max(q.getcolors(), key=lambda c: c[0])[1]
            pal = q.getpalette()
            px[x, y] = (pal[idx * 3], pal[idx * 3 + 1], pal[idx * 3 + 2])
    return out


def slice_frames(sheet, stage):
    """Cut a square sheet into GRIDxGRID cells; save each, return filenames."""
    cw, ch = sheet.width // GRID, sheet.height // GRID
    names = []
    for r in range(GRID):
        for c in range(GRID):
            n = f"frame_r{r}_c{c}.png"
            sheet.crop((c * cw, r * ch, (c + 1) * cw, (r + 1) * ch)).save(stage / n)
            names.append(n)
    return names

DIFFUSION = "flux-2-klein-base-4b-fp8.safetensors"
ENCODER = "qwen_3_4b.safetensors"
VAE = "flux2-vae.safetensors"
LORA = "pixel_4walk_small_flux2_klein_base_4b_v1.safetensors"
PROMPT = ("Create a pixel art spritesheet of the character in the image. The spritesheet "
          "is a 4 by 4 grid of four rows of frames - first row is 3 walking frames facing "
          "down and 1 frame both arms raised, second row is 3 walking frames facing left and "
          "1 frame jumping left, third row is 3 walking frames facing right and 1 frame "
          "jumping right, fourth row is 3 walking frames back view facing up and 1 frame "
          "lying on floor.")
STAGE = Path("/tmp/flux2_spritesheet_gallery")


def build_graph(ref_name, seed):
    return {
        "70": {"class_type": "UNETLoader", "inputs": {"unet_name": DIFFUSION, "weight_dtype": "default"}},
        "75": {"class_type": "LoraLoaderModelOnly", "inputs": {"model": ["70", 0], "lora_name": LORA, "strength_model": 1.0}},
        "71": {"class_type": "CLIPLoader", "inputs": {"clip_name": ENCODER, "type": "flux2"}},
        "72": {"class_type": "VAELoader", "inputs": {"vae_name": VAE}},
        "74": {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["71", 0]}},
        "76": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["71", 0]}},
        "load": {"class_type": "LoadImage", "inputs": {"image": ref_name}},
        "scale": {"class_type": "ImageScaleToTotalPixels",
                  "inputs": {"image": ["load", 0], "upscale_method": "nearest-exact", "megapixels": 1.0, "resolution_steps": 1}},
        "enc": {"class_type": "VAEEncode", "inputs": {"pixels": ["scale", 0], "vae": ["72", 0]}},
        "refpos": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["74", 0], "latent": ["enc", 0]}},
        "refneg": {"class_type": "ReferenceLatent", "inputs": {"conditioning": ["76", 0], "latent": ["enc", 0]}},
        "66": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": 512, "height": 512, "batch_size": 1}},
        "62": {"class_type": "Flux2Scheduler", "inputs": {"steps": 20, "width": 512, "height": 512}},
        "61": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "73": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "63": {"class_type": "CFGGuider", "inputs": {"model": ["75", 0], "positive": ["refpos", 0], "negative": ["refneg", 0], "cfg": 5.0}},
        "64": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["73", 0], "guider": ["63", 0], "sampler": ["61", 0], "sigmas": ["62", 0], "latent_image": ["66", 0]}},
        "65": {"class_type": "VAEDecode", "inputs": {"samples": ["64", 0], "vae": ["72", 0]}},
        "67": {"class_type": "SaveImage", "inputs": {"images": ["65", 0], "filename_prefix": "spritesheet"}},
    }


def write_gallery(ref, raw_sheet, sheet128, frames, meta):
    shutil.copyfile(ref, STAGE / ("ref_" + Path(ref).name))
    frame_cards = "".join(f'<figure class=fr><img src="{f}"><figcaption>{f[6:-4]}</figcaption></figure>' for f in frames)
    html = f"""<!doctype html><meta charset=utf-8><title>FLUX.2 4B sprite-sheet LoRA test</title>
<style>body{{background:#fafafa;color:#1a1a1a;font:15px/1.5 system-ui;margin:24px}}
img{{image-rendering:pixelated;border:1px solid #ddd;border-radius:6px}}
h2{{font-size:15px;margin:22px 0 6px}}
.row{{display:flex;gap:16px;flex-wrap:wrap;align-items:flex-start}}
.row figure img{{width:320px}}
figure{{margin:0;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px}}
figcaption{{font-size:12px;color:#666;margin-top:6px;text-align:center}}
.frames{{display:grid;grid-template-columns:repeat(4,72px);gap:8px}}
.fr{{padding:4px}} .fr img{{width:64px;height:64px}}</style>
<h1>FLUX.2 Klein 4B + 4-walk sprite-sheet LoRA</h1><p>{meta}</p>
<div class=row>
<figure><img src="ref_{Path(ref).name}"><figcaption>input character</figcaption></figure>
<figure><img src="{raw_sheet}"><figcaption>raw sheet 512&times;512</figcaption></figure>
<figure><img src="{sheet128}" style="width:320px"><figcaption>k-centroid 4&times; &rarr; 128&times;128 (32&times;32 frames)</figcaption></figure>
</div>
<h2>Sliced frames (32&times;32, shown 2&times;)</h2><div class=frames>{frame_cards}</div>"""
    (STAGE / "index.html").write_text(html)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    ref_name = stage_ref(a.ref)
    print(f"sprite-sheet test | ref {ref_name} | seed {seed} | 4B base + LoRA @1.0 | 20 steps cfg5")
    t0 = time.time()
    hist = render(build_graph(ref_name, seed))
    imgs = fetch(hist, STAGE)
    dt = time.time() - t0
    raw = imgs[0]
    sheet = Image.open(STAGE / raw)
    sheet128 = kcentroid_downscale(sheet, sheet.width // 4, sheet.height // 4)
    sheet128.save(STAGE / "sheet_128.png")
    frames = slice_frames(sheet128, STAGE)
    print(f"done in {dt:.0f}s -> {raw}, sheet_128.png, {len(frames)} frames")
    write_gallery(a.ref, raw, "sheet_128.png", frames, f"seed {seed} · 20 steps · cfg 5 · {dt:.0f}s")
    serve(STAGE, not a.no_open)
    if not a.no_open:
        print("serving; Ctrl-C to stop")
        block()


if __name__ == "__main__":
    main()
