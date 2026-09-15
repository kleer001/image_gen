#!/usr/bin/env python3
"""LivePortrait Expression Editor driver: one face -> a sheet of dialed expressions.

Validated on the production ComfyUI (:8188) with ComfyUI-AdvancedLivePortrait
installed. The workflow is `workflows/liveportrait_expression.json`.

What it does: takes one rendered face and a list of expression dial-sets, and runs
the Expression Editor once per set — the local, LoRA-free way to put an exact
emotion on a still (the open analogue of the "six emotions from one portrait" use).
Each dialed still is a candidate WAN start frame under the stills-first rule.

Why this is separate from the shot drivers: it edits a facial expression on an
existing still with continuous control, where a prompt or an expression LoRA only
steers coarsely and tends to exaggerate. It runs on the production ComfyUI (:8188)
as a custom node — no new environment, and no WAN-style hardware hazard.

Usage:
    liveportrait.py sheet.yaml [--keep]

Shot file (YAML):

    image: ./refs/face.png        # one rendered face (neutral is the best base)
    shots:
      - label: neutral
        params: {}
      - label: suppressed anger (peak)
        params: {smile: -0.2, eyebrow: -0.15, aaa: -0.1}
      - label: holding back tears
        params: {blink: 0.3, eyebrow: 0.2, woo: 0.1}

`params` keys are ExpressionEditor inputs; the driver passes them through verbatim
and leaves the rest at the workflow defaults. See examples/liveportrait_expression.example.yaml
for calibrated presets and the input ranges (small values barely register).
"""
import argparse
import json
import mimetypes
import shutil
import sys
import tempfile
import time
import urllib.request
import uuid
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
WORKFLOWS = REPO / "workflows"
COMFY_OUTPUT = REPO / "comfyui" / "output"
SERVER = "http://127.0.0.1:8188"

WORKFLOW = WORKFLOWS / "liveportrait_expression.json"
EDITOR_CLASS = "ExpressionEditor"


def load_workflow():
    wf = json.loads(WORKFLOW.read_text())
    wf.pop("_scaffold", None)
    return wf


def node_id(wf, class_type):
    for nid, node in wf.items():
        if node.get("class_type") == class_type:
            return nid
    raise KeyError(f"workflow has no node of class_type {class_type!r}")


def queue_prompt(workflow):
    body = json.dumps({"prompt": workflow, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(f"{SERVER}/prompt", data=body,
                                 headers={"Content-Type": "application/json"})
    return json.loads(urllib.request.urlopen(req).read())["prompt_id"]


def wait_for(prompt_id, timeout=300):
    deadline = time.time() + timeout
    while time.time() < deadline:
        hist = json.loads(urllib.request.urlopen(f"{SERVER}/history/{prompt_id}").read())
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(1.5)
    raise TimeoutError(f"prompt {prompt_id} did not complete in {timeout}s")


def first_output_path(result):
    # The ExpressionEditor emits a preview (type "temp"); take the SaveImage
    # result (type "output"), which is the persisted file in comfyui/output.
    for out in result.get("outputs", {}).values():
        for img in out.get("images", []):
            if img.get("type") != "output":
                continue
            return COMFY_OUTPUT / (img.get("subfolder") or "") / img["filename"]
    raise RuntimeError(f"no saved image in result: {json.dumps(result.get('status', {}))}")


def upload_image(path):
    path = Path(path).expanduser()
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
    return json.loads(urllib.request.urlopen(req).read())["name"]


def render_variant(ref_name, params):
    wf = load_workflow()
    wf[node_id(wf, "LoadImage")]["inputs"]["image"] = ref_name
    editor = wf[node_id(wf, EDITOR_CLASS)]["inputs"]
    for key, value in params.items():
        editor[key] = value
    return first_output_path(wait_for(queue_prompt(wf)))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("sheet", help="YAML: a source image and a list of expression dial-sets")
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    args = ap.parse_args()

    spec = yaml.safe_load(Path(args.sheet).read_text())
    ref_name = upload_image(spec["image"])
    print(f"[ref] uploaded {spec['image']} -> {ref_name}")

    shots = spec.get("shots", [])
    if not shots:
        sys.exit("sheet has no shots")

    serve_dir = Path(tempfile.mkdtemp(prefix="liveportrait_"))
    cards = []
    for i, shot in enumerate(shots):
        label = shot.get("label", f"variant {i + 1}")
        params = shot.get("params", {})
        print(f"[{i+1}/{len(shots)}] {label}: {params}")
        out = render_variant(ref_name, params)
        local = serve_dir / f"expr_{i+1:02d}{out.suffix}"
        shutil.copy(out, local)
        cards.append({"src": local.name, "caption": f"<b>{label}</b><br>{params}"})

    gallery.write_gallery(serve_dir, f"LivePortrait expressions — {len(cards)}", cards,
                          media="img", theme="light")
    gallery.serve_and_block(serve_dir, keep=args.keep)


if __name__ == "__main__":
    main()
