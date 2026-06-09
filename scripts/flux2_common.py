#!/usr/bin/env python3
"""Shared helpers for the FLUX.2 Klein drivers (isolated ComfyUI on :8189).

Holds the instance/model constants, the submit+wait render loop (with a single
OOM retry — ComfyUI unloads all models on a GPU OOM, so a retry runs against
freed VRAM, the documented recovery on a 24GB card holding the 9B model + 8B
encoder + VAE), image fetching, and the browser-gallery server. The three
drivers (flux2_klein, flux2_klein_edit, flux2_character_sheet) build their own
graphs and gallery HTML and route everything else through here.
"""
import json, time, shutil, functools, urllib.request, urllib.parse
import http.server, socketserver, threading, webbrowser
from pathlib import Path

HOST = "http://127.0.0.1:8189"
INPUT_DIR = Path("/media/menser/fauna/image_gen/comfyui_flux2/input")
DIFFUSION = "flux-2-klein-9b-fp8.safetensors"
ENCODER = "qwen_3_8b_fp8mixed.safetensors"
VAE = "flux2-vae.safetensors"


def submit(graph):
    data = json.dumps({"prompt": graph}).encode()
    req = urllib.request.Request(f"{HOST}/prompt", data=data, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))["prompt_id"]


def _poll(pid, timeout):
    t0 = time.time()
    while time.time() - t0 < timeout:
        h = json.load(urllib.request.urlopen(f"{HOST}/history/{pid}"))
        if pid in h:
            if h[pid]["status"].get("status_str") == "error":
                raise RuntimeError(json.dumps(h[pid].get("status"))[:500])
            return h[pid]
        time.sleep(2)
    raise TimeoutError(pid)


def render(graph, timeout=900):
    """Submit a graph and wait for its result, retrying once on a GPU OOM."""
    try:
        return _poll(submit(graph), timeout)
    except RuntimeError as e:
        if "OutOfMemory" not in str(e) and "out of memory" not in str(e).lower():
            raise
        time.sleep(3)
        return _poll(submit(graph), timeout)


def fetch(hist, stage, prefix=""):
    """Save all output images into `stage`; return their filenames."""
    out = []
    for node in hist["outputs"].values():
        for img in node.get("images", []):
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
            raw = urllib.request.urlopen(f"{HOST}/view?{q}").read()
            name = f"{prefix}{img['filename']}"
            (Path(stage) / name).write_bytes(raw)
            out.append(name)
    return out


def fetch_first(hist, dst):
    """Save the first output image to `dst`; return the path."""
    for node in hist["outputs"].values():
        for img in node.get("images", []):
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
            Path(dst).write_bytes(urllib.request.urlopen(f"{HOST}/view?{q}").read())
            return Path(dst)
    raise RuntimeError("no image in history outputs")


def stage_ref(path):
    """Copy a reference image into ComfyUI's input/ so LoadImage can read it."""
    src = Path(path)
    if not src.is_file():
        raise FileNotFoundError(path)
    INPUT_DIR.mkdir(parents=True, exist_ok=True)
    dst = INPUT_DIR / f"editref_{src.name}"
    shutil.copyfile(src, dst)
    return dst.name


def serve(stage, open_browser=True, base_port=8765):
    """Serve `stage` over HTTP on the first free port from base_port; print the
    URL and optionally open a browser. Returns the URL (daemon thread)."""
    port = base_port
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(stage))
    while True:
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", port), handler); break
        except OSError:
            port += 1
    url = f"http://127.0.0.1:{port}/index.html"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"GALLERY: {url}")
    if open_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    return url


def block():
    """Keep the daemon gallery server alive until interrupted."""
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        pass
