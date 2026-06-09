#!/usr/bin/env python3
"""FLUX.2 Klein 9B character reference-sheet generator (isolated ComfyUI :8189).

Emits a multi-panel character sheet with identity locked across panels: panel 1
is a text-to-image seed (the character on a neutral-gray background under soft
directional key light — the character-sheet craft from CLAUDE.md); panels 2..N
are reference-driven edits of panel 1 (same face/outfit, new angle/crop). The
result is the `reference:` material the storyboard/video drivers consume.

Composes the two Klein drivers:
  panel 1  -> flux2_klein.build_graph        (text-to-image)
  panel k  -> flux2_klein_edit.build_graph   (reference edit, panel 1 as ref)

Runs on the isolated comfyui_flux2/ instance. Distilled 9B (4 steps, cfg 1).

Usage:
  scripts/flux2_character_sheet.py "character description" [--seed N] [--steps 4]
       [--width 832] [--height 1216] [--no-open]
"""
import argparse, time, random, shutil, urllib.request, urllib.parse
import http.server, socketserver, threading, webbrowser
from pathlib import Path

# sibling imports (scripts/ is on sys.path when run directly)
from flux2_klein import build_graph as t2i_graph
from flux2_klein_edit import build_graph as edit_graph, submit, wait, stage_ref, HOST

STAGE = Path("/tmp/flux2_character_sheet_gallery")
GRAY_SUFFIX = (", full character on a solid neutral-gray background, soft directional "
               "key light with gentle falloff, even studio framing, photographic")

# (label, edit instruction for panels 2..N). Panel 1 is the seed t2i.
PANELS = [
    ("3/4 view", "Show the exact same character in a full-body three-quarter view, "
                 "identical face, hair, and outfit"),
    ("Side profile", "Show the exact same character in a side profile, head-and-shoulders, "
                     "identical face, hair, and outfit"),
    ("Face close-up", "Close-up of the exact same character's face, neutral expression, "
                      "identical features"),
]


def run(graph):
    """Submit + wait. On a GPU OOM, ComfyUI unloads all models, so one retry
    runs against freed VRAM — the documented recovery on a 24GB card holding
    the 9B model + 8B encoder + VAE across sequential panels."""
    try:
        return wait(submit(graph))
    except RuntimeError as e:
        if "OutOfMemory" not in str(e) and "out of memory" not in str(e).lower():
            raise
        time.sleep(3)
        return wait(submit(graph))


def fetch_first(hist, dst):
    for node in hist["outputs"].values():
        for img in node.get("images", []):
            q = urllib.parse.urlencode({"filename": img["filename"], "subfolder": img.get("subfolder", ""), "type": img.get("type", "output")})
            dst.write_bytes(urllib.request.urlopen(f"{HOST}/view?{q}").read())
            return dst
    raise RuntimeError("no image in history outputs")


def gallery(desc, panels, open_browser):
    cards = "".join(f'<figure><img src="{p.name}"><figcaption>{lbl}</figcaption></figure>' for lbl, p in panels)
    html = f"""<!doctype html><meta charset=utf-8><title>Character sheet — Klein 9B</title>
<style>body{{background:#fafafa;color:#1a1a1a;font:15px/1.5 system-ui,sans-serif;margin:24px}}
.p{{background:#fff;border:1px solid #ddd;padding:12px 16px;border-radius:8px;max-width:1200px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:16px;margin-top:20px;max-width:1200px}}
figure{{margin:0;background:#fff;border:1px solid #ddd;border-radius:8px;padding:10px}}
img{{width:100%;height:auto;border-radius:4px;display:block}}
figcaption{{margin-top:6px;font-size:13px;color:#444;text-align:center}}</style>
<h1>Character reference sheet — FLUX.2 Klein 9B</h1>
<div class=p><b>identity locked across panels via reference edit</b><br>{desc}</div>
<div class=grid>{cards}</div>"""
    (STAGE / "index.html").write_text(html)
    port = 8765
    import functools
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(STAGE))
    while True:
        try:
            httpd = socketserver.TCPServer(("127.0.0.1", port), handler); break
        except OSError:
            port += 1
    url = f"http://127.0.0.1:{port}/index.html"
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    print(f"GALLERY: {url}")
    if open_browser:
        try: webbrowser.open(url)
        except Exception: pass
    return url


def main():
    ap = argparse.ArgumentParser(description="FLUX.2 Klein 9B character reference sheet on :8189")
    ap.add_argument("description", help="character description (e.g. 'a wiry man in his 40s, shaved head, leather jacket')")
    ap.add_argument("--seed", type=int, default=None)
    ap.add_argument("--steps", type=int, default=4)
    ap.add_argument("--width", type=int, default=832)
    ap.add_argument("--height", type=int, default=1216)
    ap.add_argument("--no-open", action="store_true")
    a = ap.parse_args()
    seed = a.seed if a.seed is not None else random.randint(0, 2**31 - 1)

    if STAGE.exists():
        shutil.rmtree(STAGE)
    STAGE.mkdir(parents=True)

    panels = []
    # Panel 1: seed (text-to-image) — full-body front on gray bg, soft key
    seed_prompt = f"full-body front view of {a.description}{GRAY_SUFFIX}"
    print(f"[panel 1/{len(PANELS)+1}] seed t2i | seed {seed}")
    t0 = time.time()
    hist = run(t2i_graph(seed_prompt, "", seed, a.steps, a.width, a.height, 1.0, 1))
    p1 = fetch_first(hist, STAGE / "panel_01_front.png")
    panels.append(("Front (seed)", p1))
    print(f"  done {time.time()-t0:.0f}s")

    # Panels 2..N: reference edits of panel 1 (identity locked)
    ref_name = stage_ref(str(p1))
    for i, (label, instr) in enumerate(PANELS, start=2):
        print(f"[panel {i}/{len(PANELS)+1}] {label}")
        t0 = time.time()
        prompt = f"{instr}{GRAY_SUFFIX}"
        hist = run(edit_graph(prompt, [ref_name], seed + i, a.steps, 1.0))
        pk = fetch_first(hist, STAGE / f"panel_{i:02d}.png")
        panels.append((label, pk))
        print(f"  done {time.time()-t0:.0f}s")

    gallery(a.description, panels, not a.no_open)
    if not a.no_open:
        print("serving; Ctrl-C to stop")
        try:
            while True: time.sleep(3600)
        except KeyboardInterrupt:
            pass


if __name__ == "__main__":
    main()
