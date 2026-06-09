#!/usr/bin/env python3
"""Same-prompt A/B: Flux.1-dev (20-step) vs FLUX.2 Klein 9B distilled (4-step).

Runs both graphs against the isolated ComfyUI on :8189 (which reads the shared
models/ dir), collects the outputs, and opens a side-by-side browser gallery.

Both sides use the canonical ComfyUI template wiring for their model family, the
same prompt / seed / resolution. Sampler config differs by model (each uses its
family's recommended steps/cfg) — that's the fair comparison, not identical knobs.
"""
import json, time, urllib.request, urllib.parse, http.server, socketserver, threading, webbrowser, shutil
from pathlib import Path

HOST = "http://127.0.0.1:8189"
PROMPT = ("A weathered lighthouse keeper in his late sixties, deep-set eyes, "
          "salt-and-pepper stubble, hand-knit wool sweater, standing on a "
          "storm-battered pier at dusk; soft directional rim light, volumetric "
          "sea mist, shallow depth of field, muted teal-and-amber palette, "
          "fine natural skin texture, photographic, subtle film grain")
SEED = 42
W = H = 1024
STAGE = Path("/tmp/klein_compare_gallery")


def flux1dev_graph():
    return {
        "1": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux1-dev.safetensors", "weight_dtype": "fp8_e4m3fn"}},
        "2": {"class_type": "DualCLIPLoader", "inputs": {"clip_name1": "clip_l.safetensors", "clip_name2": "t5xxl_fp16.safetensors", "type": "flux"}},
        "3": {"class_type": "VAELoader", "inputs": {"vae_name": "ae.safetensors"}},
        "4": {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["2", 0]}},
        "5": {"class_type": "ConditioningZeroOut", "inputs": {"conditioning": ["4", 0]}},
        "6": {"class_type": "EmptySD3LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "7": {"class_type": "KSampler", "inputs": {"model": ["1", 0], "positive": ["4", 0], "negative": ["5", 0],
              "latent_image": ["6", 0], "seed": SEED, "steps": 20, "cfg": 1.0,
              "sampler_name": "euler", "scheduler": "simple", "denoise": 1.0}},
        "8": {"class_type": "VAEDecode", "inputs": {"samples": ["7", 0], "vae": ["3", 0]}},
        "9": {"class_type": "SaveImage", "inputs": {"images": ["8", 0], "filename_prefix": "cmp_flux1dev"}},
    }


def klein9b_graph():
    return {
        "10": {"class_type": "UNETLoader", "inputs": {"unet_name": "flux-2-klein-9b-fp8.safetensors", "weight_dtype": "default"}},
        "11": {"class_type": "CLIPLoader", "inputs": {"clip_name": "qwen_3_8b_fp8mixed.safetensors", "type": "flux2"}},
        "12": {"class_type": "VAELoader", "inputs": {"vae_name": "flux2-vae.safetensors"}},
        "13": {"class_type": "CLIPTextEncode", "inputs": {"text": PROMPT, "clip": ["11", 0]}},
        "14": {"class_type": "CLIPTextEncode", "inputs": {"text": "", "clip": ["11", 0]}},
        "15": {"class_type": "CFGGuider", "inputs": {"model": ["10", 0], "positive": ["13", 0], "negative": ["14", 0], "cfg": 1.0}},
        "16": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "euler"}},
        "17": {"class_type": "Flux2Scheduler", "inputs": {"steps": 4, "width": W, "height": H}},
        "18": {"class_type": "RandomNoise", "inputs": {"noise_seed": SEED}},
        "19": {"class_type": "EmptyFlux2LatentImage", "inputs": {"width": W, "height": H, "batch_size": 1}},
        "20": {"class_type": "SamplerCustomAdvanced", "inputs": {"noise": ["18", 0], "guider": ["15", 0],
               "sampler": ["16", 0], "sigmas": ["17", 0], "latent_image": ["19", 0]}},
        "21": {"class_type": "VAEDecode", "inputs": {"samples": ["20", 0], "vae": ["12", 0]}},
        "22": {"class_type": "SaveImage", "inputs": {"images": ["21", 0], "filename_prefix": "cmp_klein9b"}},
    }


def submit(graph):
    data = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{HOST}/prompt", data=data, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["prompt_id"]


def wait(pid, timeout=900):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            return h[pid]
        time.sleep(2)
    raise TimeoutError(pid)


def fetch_images(hist, dst_prefix):
    saved = []
    for node in hist["outputs"].values():
        for img in node.get("images", []):
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
            raw = urllib.request.urlopen(f"{HOST}/view?{q}").read()
            out = STAGE / f"{dst_prefix}_{img['filename']}"
            out.write_bytes(raw)
            saved.append(out.name)
    return saved


def run(label, graph, prefix):
    print(f"[{label}] submitting...")
    pid = submit(graph)
    t0 = time.time()
    hist = wait(pid)
    imgs = fetch_images(hist, prefix)
    print(f"[{label}] done in {time.time()-t0:.0f}s -> {imgs}")
    return imgs


def gallery(results):
    cards = ""
    for label, sub, imgs in results:
        for im in imgs:
            cards += f'<figure><img src="{im}"><figcaption><b>{label}</b><br>{sub}</figcaption></figure>'
    html = f"""<!doctype html><meta charset=utf-8><title>Flux.1-dev vs FLUX.2 Klein 9B</title>
<style>body{{background:#fafafa;color:#1a1a1a;font:15px/1.5 system-ui,sans-serif;margin:24px}}
h1{{font-size:20px}} .p{{background:#fff;border:1px solid #ddd;padding:12px 16px;border-radius:8px;max-width:1100px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-top:20px;max-width:1100px}}
figure{{margin:0;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px}}
img{{width:100%;height:auto;border-radius:4px;display:block}}
figcaption{{margin-top:8px;font-size:13px;color:#444}}</style>
<h1>Same prompt · seed {SEED} · {W}×{H}</h1>
<div class=p><b>Prompt:</b> {PROMPT}</div>
<div class=grid>{cards}</div>"""
    (STAGE / "index.html").write_text(html)


def serve():
    import functools
    port = 8765
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(STAGE))
    while True:
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
            break
        except OSError:
            port += 1
    url = f"http://127.0.0.1:{port}/index.html"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"\nGALLERY: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    return url


if __name__ == "__main__":
    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)
    results = [
        ("FLUX.2 Klein 9B", "distilled · 4 steps · cfg 1 · euler", *[klein9b_graph]),
        ("Flux.1-dev", "fp8 · 20 steps · cfg 1 · euler/simple", *[flux1dev_graph]),
    ]
    out = []
    for label, sub, gfn in results:
        imgs = run(label, gfn(), "klein9b" if "Klein" in label else "flux1dev")
        out.append((label, sub, imgs))
    gallery(out)
    serve()
    print("Serving until Ctrl-C (or process kill).")
    while True:
        time.sleep(3600)
