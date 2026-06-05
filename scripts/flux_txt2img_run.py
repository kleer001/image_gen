#!/usr/bin/env python3
"""Minimal headless Flux txt2img runner: prompt -> one png. Unbuffered, no serve loop.

Drives workflows/flux_txt2img.json by patching nodes directly. Safe for unattended batch.

Usage:
    flux_txt2img_run.py <out.png> "<prompt>" [w] [h] [seed] [steps] [guidance]
"""
import json, sys, time, urllib.request, uuid, shutil
from pathlib import Path

SERVER = "http://127.0.0.1:8188"
REPO = Path("/media/menser/fauna/image_gen")
WF = REPO / "workflows" / "flux_txt2img.json"
OUT = REPO / "comfyui" / "output"

def log(m): print(m, flush=True)

def set_node(w, nid, key, val):
    w[nid]["inputs"][key] = val

def main():
    out, prompt = sys.argv[1], sys.argv[2]
    w_   = int(sys.argv[3]) if len(sys.argv) > 3 else 1344
    h_   = int(sys.argv[4]) if len(sys.argv) > 4 else 768
    seed = int(sys.argv[5]) if len(sys.argv) > 5 else 42
    steps= int(sys.argv[6]) if len(sys.argv) > 6 else 24
    guid = float(sys.argv[7]) if len(sys.argv) > 7 else 3.5

    wf = json.loads(WF.read_text())
    set_node(wf, "6", "text", prompt)        # CLIPTextEncode
    set_node(wf, "27", "width", w_)          # EmptySD3LatentImage
    set_node(wf, "27", "height", h_)
    set_node(wf, "25", "noise_seed", seed)   # RandomNoise
    set_node(wf, "17", "steps", steps)       # BasicScheduler
    set_node(wf, "26", "guidance", guid)     # FluxGuidance

    body = json.dumps({"prompt": wf, "client_id": uuid.uuid4().hex}).encode()
    req = urllib.request.Request(f"{SERVER}/prompt", data=body, headers={"Content-Type": "application/json"})
    pid = json.loads(urllib.request.urlopen(req).read())["prompt_id"]
    log(f"queued {pid}: {out} ({w_}x{h_}, seed {seed})")

    deadline = time.time() + 600
    while time.time() < deadline:
        hist = json.loads(urllib.request.urlopen(f"{SERVER}/history/{pid}").read())
        if pid in hist:
            if hist[pid].get("status", {}).get("status_str") == "error":
                log("ERROR: execution error"); sys.exit(2)
            for node_out in hist[pid].get("outputs", {}).values():
                for item in node_out.get("images", []):
                    p = OUT / item.get("subfolder", "") / item["filename"]
                    if p.exists():
                        Path(out).parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy(p, out); log(f"SAVED {out}"); return
            log("DONE but no image"); sys.exit(3)
        time.sleep(2)
    log("TIMEOUT"); sys.exit(4)

if __name__ == "__main__":
    main()
