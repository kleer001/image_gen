#!/usr/bin/env python3
"""LivePortrait retargeting driver: driving performance video -> character portrait.

SCAFFOLD — schema-verified, render UNTESTED. The workflow
`scaffolds/liveportrait_retarget.json` uses nodes confirmed present on the
production ComfyUI (AdvancedLivePortrait, VHS_LoadVideo, VHS_VideoCombine), but no
end-to-end render has been run — that needs a real driving performance clip on the
rig. See /TODO.md before relying on this. Once a render is confirmed, promote the
workflow into workflows/ and repoint WORKFLOW.

What it does: transfers the facial performance from a driving video (an actor on a
webcam) onto one character portrait — the open analogue of Runway Act-One/Act-Two.
The driving clip supplies the acting; the portrait supplies who is acting. This is
the highest-fidelity local emotional-performance route, because a human performs the
beat instead of it being described.

Runs on the production ComfyUI (:8188) as a custom node — no new environment, and
the model is light (no WAN-style hardware hazard).

Usage:
    liveportrait_retarget.py driving.mp4 portrait.png [--eyes 0.0] [--mouth 0.0]
        [--fps 24] [--keep]

`--eyes` / `--mouth` are the retargeting_eyes / retargeting_mouth strengths (0..1):
how much of the driving eye and mouth motion to carry onto the portrait.
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import gallery  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
SCAFFOLDS = REPO / "scaffolds"
COMFY_OUTPUT = REPO / "comfyui" / "output"
COMFY_INPUT = REPO / "comfyui" / "input"
SERVER = "http://127.0.0.1:8188"

WORKFLOW = SCAFFOLDS / "liveportrait_retarget.json"


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


def wait_for(prompt_id, timeout=1800):
    deadline = time.time() + timeout
    while time.time() < deadline:
        hist = json.loads(urllib.request.urlopen(f"{SERVER}/history/{prompt_id}").read())
        if prompt_id in hist:
            return hist[prompt_id]
        time.sleep(2)
    raise TimeoutError(f"prompt {prompt_id} did not complete in {timeout}s")


def first_video_path(result):
    for out in result.get("outputs", {}).values():
        for item in out.get("gifs", []):
            fp = item.get("fullpath")
            if fp and Path(fp).exists():
                return Path(fp)
            p = COMFY_OUTPUT / item.get("subfolder", "") / item["filename"]
            if p.exists():
                return p
    raise FileNotFoundError("no video output found in prompt history")


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


def stage_video(path):
    """Copy the driving clip into comfyui/input/ so VHS_LoadVideo finds it by name."""
    path = Path(path).expanduser()
    COMFY_INPUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(path, COMFY_INPUT / path.name)
    return path.name


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("driving", help="driving performance video (an actor's face)")
    ap.add_argument("portrait", help="character portrait to drive")
    ap.add_argument("--eyes", type=float, default=0.0, help="retargeting_eyes strength 0..1")
    ap.add_argument("--mouth", type=float, default=0.0, help="retargeting_mouth strength 0..1")
    ap.add_argument("--fps", type=int, default=24, help="output frame rate")
    ap.add_argument("--keep", action="store_true", help="keep gallery dir after exit")
    args = ap.parse_args()

    wf = load_workflow()
    wf[node_id(wf, "LoadImage")]["inputs"]["image"] = upload_image(args.portrait)
    wf[node_id(wf, "VHS_LoadVideo")]["inputs"]["video"] = stage_video(args.driving)
    editor = wf[node_id(wf, "AdvancedLivePortrait")]["inputs"]
    editor["retargeting_eyes"] = args.eyes
    editor["retargeting_mouth"] = args.mouth
    wf[node_id(wf, "VHS_VideoCombine")]["inputs"]["frame_rate"] = args.fps

    print(f"retargeting {args.driving} -> {args.portrait} (eyes {args.eyes}, mouth {args.mouth})")
    out = first_video_path(wait_for(queue_prompt(wf)))

    serve_dir = Path(tempfile.mkdtemp(prefix="liveportrait_retarget_"))
    local = serve_dir / f"retarget{out.suffix}"
    shutil.copy(out, local)
    gallery.write_gallery(serve_dir, "LivePortrait retarget", [{"src": local.name,
                          "caption": f"{Path(args.driving).name} → {Path(args.portrait).name}"}],
                          media="video", theme="dark")
    gallery.serve_and_block(serve_dir, keep=args.keep)


if __name__ == "__main__":
    main()
