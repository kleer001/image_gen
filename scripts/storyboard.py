#!/usr/bin/env python3
"""Storyboard driver: shot list -> panel images -> HTML gallery in browser.

Uses ComfyUI HTTP API directly (no MCP required). Identity is preserved across
panels via Flux Kontext: each panel after the first is generated as an
in-context edit of the reference image (user-supplied or panel-1-generated).

Usage:
    storyboard.py shots.yaml [--keep]

Shot list format (YAML):

    reference: ./refs/hero.png        # optional; if absent, panel 1 is seeded
    lora: film-storyboard.safetensors
    lora_weight: 0.85
    guidance: 2.5
    steps: 24
    seed: 42                          # base seed; per-panel = base + index
    width: 1024                       # only used for seed (no-reference) panel 1
    height: 1024
    style_suffix: "..."               # optional; appended to every panel prompt
                                      # (cinematic depth/light). "" disables it.
    shots:
      - "wide establishing shot, hero on cliff at dawn, storyboarding"
      - "medium shot, hero turns to face camera"
      - prompt: "close-up, determined eyes"
        seed: 9999                    # per-shot override
"""
import argparse
import json
import mimetypes
import shutil
import sys
import tempfile
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery  # noqa: E402

REPO = Path("/media/menser/fauna/image_gen")
WORKFLOWS = REPO / "workflows"
COMFY_OUTPUT = REPO / "comfyui" / "output"
COMFY_INPUT = REPO / "comfyui" / "input"
SERVER = "http://127.0.0.1:8188"

# Appended to every panel prompt at render time (not shown in captions).
# Encodes cinematic-depth craft: light the air, not just the subject — soft
# directional key, atmospheric haze, and shallow DOF read as "photographed"
# rather than "generated", and soft falloff avoids the blown-out edges that
# produce plastic-looking faces. Override in the shot list with `style_suffix:`
# (set to "" to disable).
DEFAULT_STYLE_SUFFIX = (
    "cinematic lighting, soft directional key light with gentle falloff, "
    "volumetric atmospheric haze, atmospheric perspective, shallow depth of field, "
    "no blown-out highlights"
)

PANEL_DEFAULTS = {
    "lora": "film-storyboard.safetensors",
    "lora_weight": 0.85,
    "guidance": 2.5,
    "steps": 24,
    "width": 1024,
    "height": 1024,
    "style_suffix": DEFAULT_STYLE_SUFFIX,
}


def load_workflow(name):
    return json.loads((WORKFLOWS / f"{name}.json").read_text())


def substitute_params(workflow, overrides):
    """Walk node inputs; replace any PARAM_* placeholder with overrides[<name>]."""
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        inputs = node.get("inputs", {})
        for key, val in list(inputs.items()):
            if not (isinstance(val, str) and val.startswith("PARAM_")):
                continue
            token = val[len("PARAM_"):]
            type_hint = str
            for prefix, t in (("INT_", int), ("FLOAT_", float), ("BOOL_", bool), ("STR_", str)):
                if token.startswith(prefix):
                    type_hint = t
                    token = token[len(prefix):]
                    break
            param = token.lower()
            if param not in overrides:
                raise KeyError(f"workflow needs override '{param}' (placeholder {val})")
            inputs[key] = type_hint(overrides[param])
    return workflow


def queue_prompt(workflow):
    body = json.dumps({"prompt": workflow, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(f"{SERVER}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["prompt_id"]


def wait_for(prompt_id, timeout=600):
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = urllib.request.urlopen(f"{SERVER}/history/{prompt_id}").read()
        hist = json.loads(resp)
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(1.5)
    raise TimeoutError(f"prompt {prompt_id} did not complete in {timeout}s")


def first_output_path(result):
    for out in result.get("outputs", {}).values():
        for img in out.get("images", []):
            sub = img.get("subfolder", "")
            return COMFY_OUTPUT / sub / img["filename"]
    raise RuntimeError(f"no images in result: {json.dumps(result.get('status', {}))}")


def upload_image(path):
    """POST /upload/image so LoadImage can find it. Returns the filename ComfyUI assigned."""
    path = Path(path)
    boundary = uuid.uuid4().hex
    content_type = mimetypes.guess_type(path.name)[0] or "image/png"
    body = bytearray()
    body.extend(f"--{boundary}\r\n".encode())
    body.extend(f'Content-Disposition: form-data; name="image"; filename="{path.name}"\r\n'.encode())
    body.extend(f"Content-Type: {content_type}\r\n\r\n".encode())
    body.extend(path.read_bytes())
    body.extend(f"\r\n--{boundary}\r\nContent-Disposition: form-data; name=\"overwrite\"\r\n\r\ntrue\r\n--{boundary}--\r\n".encode())
    req = urllib.request.Request(
        f"{SERVER}/upload/image", data=bytes(body),
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["name"]


def compose_prompt(prompt, cfg):
    """Append the configured cinematic style suffix to a panel prompt.

    Kept separate from the caption text so the gallery shows the user's
    original prompt while the model receives the craft-augmented version.
    """
    suffix = cfg.get("style_suffix", "")
    return f"{prompt}, {suffix}" if suffix else prompt


def render_seed_panel(prompt, cfg, seed):
    wf = load_workflow("storyboard_seed")
    substitute_params(wf, {
        "prompt": compose_prompt(prompt, cfg),
        "lora_name": cfg["lora"],
        "lora_weight": cfg["lora_weight"],
        "guidance": cfg["guidance"],
        "steps": cfg["steps"],
        "seed": seed,
        "width": cfg["width"],
        "height": cfg["height"],
    })
    pid = queue_prompt(wf)
    return first_output_path(wait_for(pid))


def render_panel(prompt, ref_image_name, cfg, seed):
    wf = load_workflow("storyboard_panel")
    substitute_params(wf, {
        "prompt": compose_prompt(prompt, cfg),
        "ref_image": ref_image_name,
        "lora_name": cfg["lora"],
        "lora_weight": cfg["lora_weight"],
        "guidance": cfg["guidance"],
        "steps": cfg["steps"],
        "seed": seed,
    })
    pid = queue_prompt(wf)
    return first_output_path(wait_for(pid))


def normalize_shot(shot, idx, base_seed):
    if isinstance(shot, str):
        return {"prompt": shot, "seed": base_seed + idx}
    return {"prompt": shot["prompt"], "seed": shot.get("seed", base_seed + idx)}


def build_gallery(serve_dir, panels, cfg):
    cards = [{"src": p["file"],
              "caption": f"<b>{i + 1}</b> · seed {p['seed']}<br>{p['prompt']}"}
             for i, p in enumerate(panels)]
    subtitle = (f"LoRA: <code>{cfg['lora']}</code> @ {cfg['lora_weight']} · "
                f"guidance {cfg['guidance']} · steps {cfg['steps']}")
    gallery.write_gallery(serve_dir, f"Storyboard · {len(panels)} panels", cards,
                          media="img", theme="light", subtitle=subtitle,
                          footer=f"served from <code>{serve_dir}</code>")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("shotlist", help="YAML or JSON shot list")
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.shotlist).read_text())
    cfg = {**PANEL_DEFAULTS, **{k: v for k, v in spec.items() if k != "shots" and k != "reference"}}
    base_seed = int(cfg.pop("seed", int(time.time()) & 0xFFFFFFFF))
    shots = [normalize_shot(s, i, base_seed) for i, s in enumerate(spec["shots"])]
    if not shots:
        sys.exit("shot list is empty")

    serve_dir = Path(tempfile.mkdtemp(prefix="storyboard_"))
    panels = []

    # Panel 1: either render from reference, or seed a new one
    ref_path = spec.get("reference")
    start_idx = 0
    if ref_path:
        ref_name = upload_image(Path(ref_path).expanduser())
        print(f"[ref] uploaded {ref_path} -> {ref_name}")
    else:
        s = shots[0]
        print(f"[1/{len(shots)}] seeding panel 1 (no reference): {s['prompt'][:60]}...")
        out = render_seed_panel(s["prompt"], cfg, s["seed"])
        ref_name = upload_image(out)
        local = serve_dir / f"panel_01.png"
        shutil.copy(out, local)
        panels.append({"file": local.name, "prompt": s["prompt"], "seed": s["seed"]})
        start_idx = 1

    for i in range(start_idx, len(shots)):
        s = shots[i]
        print(f"[{i+1}/{len(shots)}] {s['prompt'][:70]}")
        out = render_panel(s["prompt"], ref_name, cfg, s["seed"])
        local = serve_dir / f"panel_{i+1:02d}.png"
        shutil.copy(out, local)
        panels.append({"file": local.name, "prompt": s["prompt"], "seed": s["seed"]})

    build_gallery(serve_dir, panels, cfg)
    gallery.serve_and_block(serve_dir, keep=args.keep)


if __name__ == "__main__":
    main()
