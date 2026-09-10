#!/usr/bin/env python3
"""Generate 5 banner images via ComfyUI API using Flux.1-dev + LoRAs."""
import json, time, uuid, urllib.request, urllib.parse, random, sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

SERVER = "http://127.0.0.1:8188"
OUT_DIR = str(REPO / "outputs/comfyui")
WIDTH, HEIGHT = 1216, 512

BANNERS = [
    {
        "name": "01_cyberpunk_anime",
        "lora": "Neurocore-ShadowCircuit-Flux.safetensors",
        "lora_strength": 0.85,
        "prompt": "in the style of cksc, a heroic anime warrior with glowing circuit patterns, dramatic neon city skyline at night, dynamic pose, cinematic lighting",
    },
    {
        "name": "02_painterly_fantasy",
        "lora": "PainterlyFantasy-Flux.safetensors",
        "lora_strength": 0.9,
        "prompt": "in the style of ckpf, vast enchanted landscape with ancient ruins and mystical floating islands, luminous golden atmosphere, epic scale",
    },
    {
        "name": "03_swiss_design",
        "lora": "SwissDesign-Flux.safetensors",
        "lora_strength": 0.9,
        "prompt": "sw1ssdes1gn, bold modernist grid composition, primary colors red black white, geometric abstraction, international typographic style poster",
    },
    {
        "name": "04_disney_cartoon",
        "lora": "Disney-Studios-Flux.safetensors",
        "lora_strength": 0.75,
        "prompt": "DisneyStudio cartoon, a magical workshop filled with paintbrushes and floating canvases, friendly robot painting, warm whimsical lighting, vibrant colors",
    },
    {
        "name": "05_retro_anime",
        "lora": "RetroAnime-Flux.safetensors",
        "lora_strength": 0.9,
        "prompt": "retro 1980s anime style, colorful artists creating digital paintings on glowing screens, synthwave sunset colors, nostalgic cel-shaded aesthetic",
    },
]


def make_workflow(prompt, lora, lora_strength, seed, name):
    return {
        "1": {
            "inputs": {"unet_name": "flux1-dev.safetensors", "weight_dtype": "fp8_e4m3fn"},
            "class_type": "UNETLoader",
        },
        "2": {
            "inputs": {
                "clip_name1": "t5xxl_fp8_e4m3fn.safetensors",
                "clip_name2": "clip_l.safetensors",
                "type": "flux",
            },
            "class_type": "DualCLIPLoader",
        },
        "3": {
            "inputs": {"vae_name": "flux-ae.safetensors"},
            "class_type": "VAELoader",
        },
        "4": {
            "inputs": {
                "lora_name": lora,
                "strength_model": lora_strength,
                "strength_clip": lora_strength,
                "model": ["1", 0],
                "clip": ["2", 0],
            },
            "class_type": "LoraLoader",
        },
        "5": {
            "inputs": {"text": prompt, "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "6": {
            "inputs": {"text": "", "clip": ["4", 1]},
            "class_type": "CLIPTextEncode",
        },
        "7": {
            "inputs": {"conditioning": ["5", 0], "guidance": 3.5},
            "class_type": "FluxGuidance",
        },
        "8": {
            "inputs": {"width": WIDTH, "height": HEIGHT, "batch_size": 1},
            "class_type": "EmptySD3LatentImage",
        },
        "9": {
            "inputs": {
                "seed": seed,
                "steps": 20,
                "cfg": 1.0,
                "sampler_name": "euler",
                "scheduler": "simple",
                "denoise": 1.0,
                "model": ["4", 0],
                "positive": ["7", 0],
                "negative": ["6", 0],
                "latent_image": ["8", 0],
            },
            "class_type": "KSampler",
        },
        "10": {
            "inputs": {"samples": ["9", 0], "vae": ["3", 0]},
            "class_type": "VAEDecode",
        },
        "11": {
            "inputs": {"filename_prefix": name, "images": ["10", 0]},
            "class_type": "SaveImage",
        },
    }


def queue_prompt(workflow):
    client_id = str(uuid.uuid4())
    payload = json.dumps({"prompt": workflow, "client_id": client_id}).encode()
    req = urllib.request.Request(f"{SERVER}/prompt", data=payload, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req)
    return json.loads(resp.read())["prompt_id"], client_id


def wait_for_prompt(prompt_id):
    while True:
        time.sleep(3)
        resp = urllib.request.urlopen(f"{SERVER}/history/{prompt_id}")
        history = json.loads(resp.read())
        if prompt_id in history:
            return history[prompt_id]


def get_output_images(result):
    images = []
    for node_output in result.get("outputs", {}).values():
        for img in node_output.get("images", []):
            images.append(str(REPO / "comfyui/output" / img["filename"]))
    return images


print(f"Submitting 5 banner jobs ({WIDTH}x{HEIGHT}) to ComfyUI...")
seeds = [random.randint(0, 2**32) for _ in range(5)]

for i, (banner, seed) in enumerate(zip(BANNERS, seeds)):
    print(f"\n[{i+1}/5] {banner['name']} — seed {seed}")
    workflow = make_workflow(banner["prompt"], banner["lora"], banner["lora_strength"], seed, banner["name"])
    prompt_id, _ = queue_prompt(workflow)
    print(f"       queued: {prompt_id}")
    result = wait_for_prompt(prompt_id)
    images = get_output_images(result)
    if images:
        print(f"       saved:  {images[0]}")
    else:
        print(f"       ERROR — check ComfyUI logs")
        print(json.dumps(result.get("status", {}), indent=2))

print("\nDone.")
