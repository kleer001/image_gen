#!/usr/bin/env python3
"""MiniMax H3 reference-to-video: lock subjects from reference images (:8191).

H3's ref2va path takes up to 9 reference images, and the prompt addresses them
positionally as `<Picture 1>`, `<Picture 2>` … in the order they were supplied.
That is the open analogue of Seedance-style `@image1..@imageN` conditioning, and
the reason H3 is interesting for multi-shot work: the same subjects can be
carried into a new scene without training a LoRA.

References alone drift — the model needs the identity restated in words as well,
so a prompt should both cite `<Picture i>` and describe what must stay fixed.

Usage:
  scripts/h3_ref2v.py shots.yaml [--keep] [--no-open]

Shot file (YAML):

    title: Reference harness
    seconds: 5
    width: 608
    height: 352
    seed: 7
    steps: 4
    ref_image_size: match           # or "max" — 2048px short edge, much slower
    references:                     # order sets <Picture 1>, <Picture 2>, ...
      - refs/h3/subject.jpg
      - refs/h3/prop.jpg
    shots:
      - label: establishing
        prompt: <Picture 1> holds <Picture 2> ...
"""
import argparse
import os
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gallery
from h3_t2v import (AUDIO_VAE, ENCODER, FPS, HOST, VIDEO_VAE,
                    align_length, fetch_video, lora_chain, submit, wait_for)

# Reference conditioning needs the ref2va checkpoint. The fl2va checkpoint used
# for text and keyframe work accepts the same graph and silently drops the
# reference blocks, producing a plausible video of the wrong subject — so this
# driver defaults to ref2va and its matching distill, never the fl2va pair.
REF2VA_DIFFUSION = "minimax_h3_ref2va_pruned_int8_convrot.safetensors"
REF2V_TURBO_LORA = "minimax_h3_ref2v_turbo_4step_v0.1_comfyui_bf16.safetensors"


def upload_image(path):
    """Push a reference into ComfyUI's input/ dir; return the name LoadImage wants."""
    path = Path(path)
    boundary = uuid.uuid4().hex
    body = (
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'
        f"Content-Type: application/octet-stream\r\n\r\n"
    ).encode() + path.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    req = urllib.request.Request(
        f"{HOST}/upload/image", data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"})
    import json
    return json.load(urllib.request.urlopen(req))["name"]


def build_graph(prompt, ref_names, seed, steps, width, height, length,
                ref_image_size, loras, checkpoint):
    graph = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": checkpoint, "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": ENCODER, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VIDEO_VAE}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": AUDIO_VAE}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": "res_multistep"}},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["5", 0]}},
        "14": {"class_type": "CreateVideo",
               "inputs": {"images": ["12", 0], "fps": float(FPS), "audio": ["13", 0]}},
        "15": {"class_type": "SaveVideo",
               "inputs": {"video": ["14", 0], "filename_prefix": "video/h3_ref2v",
                          "format": "mp4"}},
    }
    # One LoadImage per reference. `ref_images` is an Autogrow input, and its
    # slots are addressed by the executor's dotted dynamic-path keys —
    # "ref_images.ref_image_0", zero-indexed — which build_nested_inputs() then
    # re-nests into the dict the node's execute() receives. A nested
    # {"ref_images": {...}} is accepted without error and silently drops every
    # reference; bare "ref_image_0" raises an unexpected-keyword TypeError.
    ref_inputs = {}
    for i, name in enumerate(ref_names):
        nid = f"ref{i}"
        graph[nid] = {"class_type": "LoadImage", "inputs": {"image": name}}
        ref_inputs[f"ref_images.ref_image_{i}"] = [nid, 0]

    graph["6"] = {"class_type": "MiniMaxH3ReferenceToVideo",
                  "inputs": {"clip": ["3", 0], "vae": ["4", 0], "audio_vae": ["5", 0],
                             "prompt": prompt, "width": width, "height": height,
                             "length": length, "ref_image_size": ref_image_size,
                             **ref_inputs}}
    model = lora_chain(graph, loras)
    graph["7"] = {"class_type": "BasicGuider",
                  "inputs": {"model": model, "conditioning": ["6", 0]}}
    graph["9"] = {"class_type": "BasicScheduler",
                  "inputs": {"model": model, "scheduler": "simple",
                             "steps": steps, "denoise": 1.0}}
    graph["11"] = {"class_type": "SamplerCustomAdvanced",
                   "inputs": {"noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0],
                              "sigmas": ["9", 0], "latent_image": ["6", 1]}}
    return graph


def main():
    ap = argparse.ArgumentParser(description="MiniMax H3 reference-to-video on :8191")
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
    cfg.setdefault("ref_image_size", "match")
    cfg.setdefault("checkpoint", REF2VA_DIFFUSION)
    cfg.setdefault("loras", [[REF2V_TURBO_LORA, 1.0]])

    length = align_length(cfg["seconds"])
    stage = Path(tempfile.mkdtemp(prefix="h3_ref2v_"))
    loras = [tuple(x) for x in cfg["loras"]]

    ref_names = [upload_image(p) for p in cfg["references"]]
    print(f"{cfg['title']} — {len(cfg['shots'])} shots | {cfg['width']}x{cfg['height']} | "
          f"{length}f @ {FPS}fps | seed {cfg['seed']}")
    print(f"  checkpoint: {cfg['checkpoint']}")
    for i, (path, name) in enumerate(zip(cfg["references"], ref_names), 1):
        print(f"  <Picture {i}> = {path}")

    results = []
    for i, shot in enumerate(cfg["shots"], 1):
        print(f"  [{i}] {shot['label']} ... ", end="", flush=True)
        t0 = time.time()
        graph = build_graph(shot["prompt"], ref_names, cfg["seed"], cfg["steps"],
                            cfg["width"], cfg["height"], length,
                            cfg["ref_image_size"], loras, cfg["checkpoint"])
        clip = fetch_video(wait_for(submit(graph), cfg["timeout"]), stage)
        named = f"{i:02d}_{shot['label'].replace(' ', '_')}.mp4"
        (Path(stage) / clip).rename(Path(stage) / named)
        dt = time.time() - t0
        print(f"{dt:.0f}s")
        results.append({"label": shot["label"], "file": named,
                        "prompt": shot["prompt"], "seconds": dt})

    # Reference stills sit at the top of the page so identity drift is judgeable.
    for i, path in enumerate(cfg["references"], 1):
        (stage / f"ref{i}.jpg").write_bytes(Path(path).read_bytes())
    ref_strip = "".join(
        f'<figure><img src="ref{i}.jpg" style="max-width:260px">'
        f"<figcaption>&lt;Picture {i}&gt;<br><small>{Path(p).name}</small></figcaption></figure>"
        for i, p in enumerate(cfg["references"], 1))

    cards = [{"src": r["file"],
              "caption": f"<b>{r['label']}</b> · {r['seconds']:.0f}s<br><small>{r['prompt']}</small>"}
             for r in results]
    gallery.write_gallery(
        stage, cfg["title"], cards, media="video", theme="dark", muted=False,
        subtitle=f'<div class="grid">{ref_strip}</div>',
        footer="Unmute — H3 generates the soundtrack in the same pass as the video.")
    if a.no_open:
        print(f"gallery dir: {stage}")
        return
    gallery.serve_and_block(stage, keep=a.keep)


if __name__ == "__main__":
    main()
