#!/usr/bin/env python3
"""MiniMax H3 text-to-video (+ native audio) on the isolated ComfyUI at :8191.

H3 generates the video and its stereo soundtrack in one sampling pass — the AV
latent is a nested (video, audio) pair that both VAEs decode from. Frame count
snaps to the model's 17k+5 grid at 24 fps, so --seconds is rounded up to the
next valid length.

Usage:
  scripts/h3_t2v.py "a prompt" [--seconds 3] [--width 608] [--height 352]
                    [--steps 4] [--seed N] [--keep] [--no-open]
"""
import argparse
import json
import os
import random
import sys
import tempfile
import time
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import gallery

HOST = "http://127.0.0.1:8191"
DIFFUSION = "minimax_h3_fl2va_pruned_int8_convrot.safetensors"
ENCODER = "qwen3vl_32b_minimax_h3_nvfp4_awq.safetensors"
VIDEO_VAE = "minimax_h3_video_vae_fp16.safetensors"
AUDIO_VAE = "minimax_h3_audio_vae_fp32.safetensors"
TURBO_LORA = "minimax_h3_fl2v_turbo_4step_v1.0_768p_comfyui_bf16.safetensors"
FPS = 24


def align_length(seconds):
    """Frame count for `seconds` at 24 fps, snapped up to the model's 17k+5 grid."""
    n = max(5, round(seconds * FPS))
    while n % 17 != 5:
        n += 1
    return n


def lora_chain(graph, loras):
    """Chain LoraLoaderModelOnly nodes off the UNETLoader; return the last model ref."""
    src = ["1", 0]
    for i, (name, strength) in enumerate(loras):
        nid = f"2_{i}"
        graph[nid] = {"class_type": "LoraLoaderModelOnly",
                      "inputs": {"model": src, "lora_name": name, "strength_model": strength}}
        src = [nid, 0]
    return src


def build_graph(prompt, seed, steps, width, height, length, loras=((TURBO_LORA, 1.0),),
                sampler="res_multistep", scheduler="simple", latent_scale=None):
    graph = {
        "1": {"class_type": "UNETLoader",
              "inputs": {"unet_name": DIFFUSION, "weight_dtype": "default"}},
        "3": {"class_type": "CLIPLoader",
              "inputs": {"clip_name": ENCODER, "type": "minimax", "device": "default"}},
        "4": {"class_type": "VAELoader", "inputs": {"vae_name": VIDEO_VAE}},
        "5": {"class_type": "VAELoader", "inputs": {"vae_name": AUDIO_VAE}},
        "6": {"class_type": "MiniMaxH3ImageToVideo",
              "inputs": {"clip": ["3", 0], "vae": ["4", 0], "prompt": prompt,
                         "width": width, "height": height, "length": length}},
        "7": {"class_type": "BasicGuider",
              "inputs": {"model": None, "conditioning": ["6", 0]}},
        "8": {"class_type": "KSamplerSelect", "inputs": {"sampler_name": sampler}},
        "9": {"class_type": "BasicScheduler",
              "inputs": {"model": None, "scheduler": scheduler, "steps": steps, "denoise": 1.0}},
        "10": {"class_type": "RandomNoise", "inputs": {"noise_seed": seed}},
        "11": {"class_type": "SamplerCustomAdvanced",
               "inputs": {"noise": ["10", 0], "guider": ["7", 0], "sampler": ["8", 0],
                          "sigmas": ["9", 0], "latent_image": ["6", 1]}},
        "12": {"class_type": "VAEDecode", "inputs": {"samples": ["11", 0], "vae": ["4", 0]}},
        "13": {"class_type": "VAEDecodeAudio", "inputs": {"samples": ["11", 0], "vae": ["5", 0]}},
        "14": {"class_type": "CreateVideo",
               "inputs": {"images": ["12", 0], "fps": float(FPS), "audio": ["13", 0]}},
        # codec is left off on purpose: SaveVideo expects it as a dict and
        # defaults to {"codec": "auto"}, which resolves to h264 inside mp4.
        "15": {"class_type": "SaveVideo",
               "inputs": {"video": ["14", 0], "filename_prefix": "video/h3_t2v",
                          "format": "mp4"}},
    }
    # Scaling the latent before decode is the community's "make it less contrasty"
    # trick, applied between the sampler and the VAE decode.
    if latent_scale is not None:
        graph["11b"] = {"class_type": "LatentMultiply",
                        "inputs": {"samples": ["11", 0], "multiplier": float(latent_scale)}}
        graph["12"]["inputs"]["samples"] = ["11b", 0]
        graph["13"]["inputs"]["samples"] = ["11b", 0]

    model = lora_chain(graph, loras)
    graph["7"]["inputs"]["model"] = model
    graph["9"]["inputs"]["model"] = model
    return graph


def submit(graph):
    data = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{HOST}/prompt", data=data,
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["prompt_id"]


def wait_for(prompt_id, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        hist = json.load(urllib.request.urlopen(f"{HOST}/history/{prompt_id}"))
        if prompt_id in hist:
            status = hist[prompt_id]["status"]
            if status.get("status_str") == "error":
                raise RuntimeError(json.dumps(status)[:2000])
            return hist[prompt_id]
        time.sleep(3)
    raise TimeoutError(f"prompt {prompt_id} did not finish in {timeout}s")


def fetch_video(hist, stage):
    """SaveVideo reports its file under the 'images' key (PreviewVideo.as_dict)."""
    for node_out in hist["outputs"].values():
        for item in node_out.get("images", []):
            q = urllib.parse.urlencode({"filename": item["filename"],
                                        "subfolder": item.get("subfolder", ""),
                                        "type": item.get("type", "output")})
            raw = urllib.request.urlopen(f"{HOST}/view?{q}").read()
            dst = Path(stage) / item["filename"]
            dst.write_bytes(raw)
            return item["filename"]
    raise RuntimeError("no video in prompt history outputs")


def main():
    ap = argparse.ArgumentParser(description="MiniMax H3 text-to-video+audio on :8191")
    ap.add_argument("prompt")
    ap.add_argument("--seconds", type=float, default=3.0)
    ap.add_argument("--width", type=int, default=608)
    ap.add_argument("--height", type=int, default=352)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--timeout", type=int, default=3600)
    ap.add_argument("--keep", action="store_true", help="keep the gallery dir on exit")
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()

    seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)
    length = align_length(a.seconds)
    stage = Path(tempfile.mkdtemp(prefix="h3_t2v_"))

    print(f"MiniMax H3 | {a.width}x{a.height} | {length}f @ {FPS}fps "
          f"({length / FPS:.2f}s) | {a.steps} steps | seed {seed}")
    t0 = time.time()
    hist = wait_for(submit(build_graph(a.prompt, seed, a.steps, a.width, a.height, length)),
                    a.timeout)
    clip = fetch_video(hist, stage)
    dt = time.time() - t0
    print(f"done in {dt / 60:.1f} min -> {stage / clip}")

    caption = (f"<b>{a.width}x{a.height}</b> · {length}f @ {FPS}fps ({length / FPS:.2f}s) · "
               f"{a.steps} steps · seed {seed} · {dt / 60:.1f} min<br>{a.prompt}")
    gallery.write_gallery(stage, "MiniMax H3 — text to video + audio",
                          [{"src": clip, "caption": caption}],
                          media="video", theme="dark", muted=False,
                          footer="Unmute the player — H3 generates the soundtrack in the same pass.")
    if a.no_open:
        print(f"  gallery dir: {stage}")
        return
    gallery.serve_and_block(stage, keep=a.keep)


if __name__ == "__main__":
    main()
