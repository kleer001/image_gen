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
import argparse, time, random, shutil, sys, os
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from flux2_common import render, fetch_first, stage_ref, serve, block
from flux2_klein import build_graph as t2i_graph
from flux2_klein_edit import build_graph as edit_graph

STAGE = Path("/tmp/flux2_character_sheet_gallery")
GRAY_SUFFIX = (", full character on a solid neutral-gray background, soft directional "
               "key light with gentle falloff, even studio framing, photographic")

# (label, edit instruction for panels 2..N). Panel 1 is the seed t2i.
# Angles are chosen for what the distilled reference-edit hits reliably: it snaps
# front<->profile cleanly but won't hold an intermediate 3/4 turn (use the base
# model + more steps for true 3/4). Hence a front/profile/back/face turnaround.
PANELS = [
    ("Side profile", "Show the exact same character from a direct side profile, body and "
                     "head turned 90 degrees to the side, full body, identical face, hair, and outfit"),
    ("Back view", "Show the exact same character from directly behind, full-body back view, "
                  "identical hair and outfit"),
    ("Face close-up", "Close-up of the exact same character's face, neutral expression, "
                      "identical features"),
]


def write_gallery(desc, panels):
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
    hist = render(t2i_graph(seed_prompt, "", seed, a.steps, a.width, a.height, 1.0, 1))
    p1 = fetch_first(hist, STAGE / "panel_01_front.png")
    panels.append(("Front (seed)", p1))
    print(f"  done {time.time()-t0:.0f}s")

    # Panels 2..N: reference edits of panel 1 (identity locked)
    ref_name = stage_ref(str(p1))
    for i, (label, instr) in enumerate(PANELS, start=2):
        print(f"[panel {i}/{len(PANELS)+1}] {label}")
        t0 = time.time()
        prompt = f"{instr}{GRAY_SUFFIX}"
        hist = render(edit_graph(prompt, [ref_name], seed + i, a.steps, 1.0))
        pk = fetch_first(hist, STAGE / f"panel_{i:02d}.png")
        panels.append((label, pk))
        print(f"  done {time.time()-t0:.0f}s")

    write_gallery(a.description, panels)
    serve(STAGE, not a.no_open)
    if not a.no_open:
        print("serving; Ctrl-C to stop")
        block()


if __name__ == "__main__":
    main()
