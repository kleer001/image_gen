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
    shots:
      - "wide establishing shot, hero on cliff at dawn, storyboarding"
      - "medium shot, hero turns to face camera"
      - prompt: "close-up, determined eyes"
        seed: 9999                    # per-shot override
"""
import argparse
import http.server
import json
import mimetypes
import os
import shutil
import socket
import socketserver
import subprocess
import sys
import tempfile
import threading
import time
import urllib.parse
import urllib.request
import uuid
from pathlib import Path

import yaml

REPO = Path("/media/menser/fauna/image_gen")
WORKFLOWS = REPO / "workflows"
COMFY_OUTPUT = REPO / "comfyui" / "output"
COMFY_INPUT = REPO / "comfyui" / "input"
SERVER = "http://127.0.0.1:8188"

PANEL_DEFAULTS = {
    "lora": "film-storyboard.safetensors",
    "lora_weight": 0.85,
    "guidance": 2.5,
    "steps": 24,
    "width": 1024,
    "height": 1024,
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


def render_seed_panel(prompt, cfg, seed):
    wf = load_workflow("storyboard_seed")
    substitute_params(wf, {
        "prompt": prompt,
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
        "prompt": prompt,
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
    rows = []
    for i, p in enumerate(panels):
        rows.append(f"""
        <figure>
          <img src="{p['file']}" alt="panel {i+1}">
          <figcaption><b>{i+1}</b> · seed {p['seed']}<br>{p['prompt']}</figcaption>
        </figure>""")
    html = f"""<!doctype html>
<html><head><meta charset="utf-8"><title>Storyboard</title>
<style>
  body {{ background:#f6f3ee; color:#222; font:13px/1.4 -apple-system,system-ui,sans-serif; max-width:1200px; margin:2em auto; padding:0 1em; }}
  header {{ border-bottom:1px solid #ccc; padding-bottom:.6em; margin-bottom:1.5em; }}
  .sheet {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(320px,1fr)); gap:1.2em; }}
  figure {{ margin:0; background:#fff; border:1px solid #bbb; box-shadow:0 1px 3px rgba(0,0,0,.08); display:flex; flex-direction:column; }}
  img {{ width:100%; display:block; border-bottom:1px solid #ccc; }}
  figcaption {{ padding:.5em .7em; font-size:12px; color:#333; min-height:3em; }}
  footer {{ margin-top:2em; padding-top:1em; border-top:1px solid #ccc; font-size:12px; color:#666; }}
  code {{ background:#eae6df; padding:1px 4px; border-radius:3px; }}
</style></head>
<body>
<header>
  <h1>Storyboard · {len(panels)} panels</h1>
  <div>LoRA: <code>{cfg['lora']}</code> @ {cfg['lora_weight']} · guidance {cfg['guidance']} · steps {cfg['steps']}</div>
</header>
<div class="sheet">{''.join(rows)}</div>
<footer>served from <code>{serve_dir}</code></footer>
</body></html>
"""
    (Path(serve_dir) / "index.html").write_text(html)


def free_port(start=8765):
    for port in range(start, start + 50):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    raise RuntimeError("no free port in 8765..8814")


def serve(serve_dir, port):
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=serve_dir, **kw)
    httpd = socketserver.TCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def open_in_browser(url):
    if not (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return False
    try:
        subprocess.Popen(["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return True
    except FileNotFoundError:
        return False


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
    port = free_port()
    httpd = serve(str(serve_dir), port)
    url = f"http://localhost:{port}/index.html"
    opened = open_in_browser(url)

    print()
    print(url)
    if not opened:
        print("(no display detected — open the URL above; forward with `ssh -L %d:localhost:%d ...` if remote)" % (port, port))
    print(f"\nCtrl-C to stop the server.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        httpd.shutdown()
        if not args.keep:
            shutil.rmtree(serve_dir, ignore_errors=True)
        print("stopped.")


if __name__ == "__main__":
    main()
