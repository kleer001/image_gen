#!/usr/bin/env python3
"""Remove glare and harsh lighting with Qwen-Image-Edit-2509 + the Light_restoration LoRA.

Runs workflows/qwen_image_edit_multiangle.json on the production stack (:8188)
with the LoRA and its fixed trigger prompt swapped in. The prompt is the one the
LoRA author specifies ("remove light and shadow, relight the image with soft
light, no obvious light spots or shadows"); the README says not to change it.

Output is at Qwen's ~1 MP bucket, not the input size. On flat-color artwork it
keeps strokes and removes glare and scratches, but lifts and desaturates colors
and tints white paper cream; scripts/match_curves.py restores the source colors.
See FLAT_ART_CLEANUP.md.

Usage:
  scripts/qwen_light_restoration.py in.png out.png [--seed N]
"""
import argparse
import json
import random
import shutil
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from storyboard import first_output_path, queue_prompt, upload_image, wait_for  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
LORA = "qwen_edit_2509_light_restoration_v2.safetensors"
PROMPT = "移除光影,使用柔和光线（无明显光斑和阴影）对图片进行重新照明"


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--seed", type=int, default=None)
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)

    wf = json.loads((REPO / "workflows" / "qwen_image_edit_multiangle.json").read_text())
    wf["3"]["inputs"]["lora_name"] = LORA
    wf["7"]["inputs"]["image"] = upload_image(Path(a.src))
    wf["9"]["inputs"]["prompt"] = PROMPT
    wf["12"]["inputs"]["seed"] = seed
    wf["14"]["inputs"]["filename_prefix"] = "qwen_light_restoration"

    t0 = time.time()
    out = first_output_path(wait_for(queue_prompt(wf), timeout=1800))
    shutil.copyfile(out, a.dst)
    print(f"seed {seed} | {time.time() - t0:.0f}s -> {a.dst}")


if __name__ == "__main__":
    main()
