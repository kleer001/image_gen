#!/usr/bin/env python3
"""Build showcase/liveportrait.html — the LivePortrait validation page.

Assembles a single self-contained HTML page (assets embedded as data URIs) from
the validation renders in comfyui/output: the retargeting clip and the four dialed
expression stills, each with its exact ExpressionEditor parameters. The stills are
cropped to the face and laid out as a 2x2 grid; the clip autoplays on a loop.

Live page: https://claude.ai/artifact/P9Hq12UyhBJGKN6FuzDVxF

The render outputs live under comfyui/output (gitignored). If they have been
cleared, re-run the LivePortrait drivers first (see PRODUCTION_WORKFLOW.md and the
LivePortrait section of TODO.md), then rebuild:

    comfyui/.venv/bin/python showcase/build_showcase.py
"""
import base64
import io
from pathlib import Path

from PIL import Image

REPO = Path(__file__).resolve().parents[1]
OUTPUT = REPO / "comfyui" / "output"
DEST = REPO / "showcase" / "liveportrait.html"

# The subject sits centred in a wide 1328x800 frame; crop to the portrait column
# so the face — where the expression reads — fills the card.
CROP = (352, 0, 976, 800)

STILLS = [
    ("Neutral", "the source frame", "—", "LivePortraitExpr_00001_.png"),
    ("Suppressed anger", "controlled peak", "eyebrow −6 · smile −0.15 · aaa −8 · pupil_y −2", "LivePortraitExpr_00004_.png"),
    ("Holding back tears", "leakage", "eyebrow +8 · blink −3 · woo +4", "LivePortraitExpr_00005_.png"),
    ("Tired half-smile", "resolve", "smile +0.5 · eee +3 · blink +1.5", "LivePortraitExpr_00006_.png"),
]
CLIP = "LivePortraitRetarget_00001.mp4"
STATS = [("Node", "ComfyUI-AdvancedLivePortrait"), ("GPU", "RTX 3090 · 24 GB"),
         ("Still render", "~2 s"), ("Clip render", "30 s")]


def jpeg_uri(path, w=760, q=88):
    im = Image.open(path).convert("RGB").crop(CROP)
    if im.width > w:
        im = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=q, optimize=True)
    return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()


def mp4_uri(path):
    return "data:video/mp4;base64," + base64.b64encode(Path(path).read_bytes()).decode()


def main():
    imgs = [jpeg_uri(OUTPUT / f) for *_, f in STILLS]
    vid = mp4_uri(OUTPUT / CLIP)
    cards = "\n".join(
        f'''      <figure class="card">
        <img src="{uri}" alt="{name}" loading="lazy">
        <figcaption>
          <div class="cap-head"><span class="cap-name">{name}</span><span class="cap-beat">{beat}</span></div>
          <div class="dials">{dials}</div>
        </figcaption>
      </figure>'''
        for (name, beat, dials, _), uri in zip(STILLS, imgs))
    stat_html = "\n".join(
        f'      <div class="stat"><span class="k">{k}</span><span class="v">{v}</span></div>'
        for k, v in STATS)

    DEST.write_text(TEMPLATE.format(vid=vid, cards=cards, stat_html=stat_html))
    print(f"wrote {DEST} ({DEST.stat().st_size / 1024:.0f} KB)")


TEMPLATE = '''<title>LivePortrait</title>
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700;800&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500&display=swap">
<style>
:root{{
  --bg:#eef1f2; --surface:#ffffff;
  --ink:#14191d; --muted:#5c6a72; --line:#d7dee1;
  --accent:#b0702f; --accent-ink:#8a561f;
  --shadow:0 1px 2px rgba(20,25,29,.04),0 8px 24px rgba(20,25,29,.06);
}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{
  --bg:#0f1417; --surface:#171e22;
  --ink:#e8edee; --muted:#8f9fa8; --line:#263137;
  --accent:#d69a5a; --accent-ink:#e6b174;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}}}}
:root[data-theme="dark"]{{
  --bg:#0f1417; --surface:#171e22;
  --ink:#e8edee; --muted:#8f9fa8; --line:#263137;
  --accent:#d69a5a; --accent-ink:#e6b174;
  --shadow:0 1px 2px rgba(0,0,0,.3),0 10px 30px rgba(0,0,0,.35);
}}
*{{box-sizing:border-box}}
body{{background:var(--bg);color:var(--ink);
  font-family:"IBM Plex Sans",system-ui,sans-serif;line-height:1.5;-webkit-font-smoothing:antialiased}}
.wrap{{max-width:1120px;margin:0 auto;padding-block:clamp(32px,6vw,64px);padding-inline:clamp(16px,4vw,40px)}}
.eyebrow{{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.16em;
  text-transform:uppercase;color:var(--accent-ink);margin:0 0 14px}}
h1{{font-family:"Archivo",sans-serif;font-weight:800;font-size:clamp(40px,9vw,76px);
  line-height:.96;letter-spacing:-.02em;margin:0;text-wrap:balance}}
.dek{{color:var(--muted);font-size:clamp(15px,2.4vw,18px);max-width:56ch;margin:18px 0 0}}
.readout{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:1px;
  background:var(--line);border:1px solid var(--line);border-radius:12px;overflow:hidden;margin:32px 0 0}}
.stat{{background:var(--surface);padding:14px 16px;display:flex;flex-direction:column;gap:3px}}
.stat .k{{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:var(--muted)}}
.stat .v{{font-family:"IBM Plex Mono",monospace;font-size:14px;color:var(--ink);font-variant-numeric:tabular-nums}}
section{{margin-top:clamp(48px,8vw,72px)}}
.sec-label{{font-family:"IBM Plex Mono",monospace;font-size:12px;letter-spacing:.14em;text-transform:uppercase;
  color:var(--muted);display:flex;align-items:baseline;gap:10px;padding-bottom:12px;border-bottom:1px solid var(--line);margin-bottom:22px}}
.sec-label b{{color:var(--ink);font-weight:600}}
.sec-label .num{{color:var(--accent-ink)}}
figure{{margin:0}}
.stage{{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:14px;box-shadow:var(--shadow)}}
.stage video{{width:100%;display:block;border-radius:8px;background:#000;aspect-ratio:1328/800}}
.stage figcaption{{display:flex;flex-wrap:wrap;gap:6px 18px;padding:14px 4px 4px;
  font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums}}
.stage figcaption b{{color:var(--ink);font-weight:500}}
.grid{{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}}
.card{{background:var(--surface);border:1px solid var(--line);border-radius:16px;overflow:hidden;
  box-shadow:var(--shadow);display:flex;flex-direction:column}}
.card img{{width:100%;display:block;aspect-ratio:624/800;object-fit:cover;border-bottom:1px solid var(--line)}}
.card figcaption{{padding:15px 18px 17px;display:flex;flex-direction:column;gap:9px}}
.cap-head{{display:flex;align-items:baseline;justify-content:space-between;gap:10px;flex-wrap:wrap}}
.cap-name{{font-family:"Archivo",sans-serif;font-weight:700;font-size:19px;color:var(--ink);letter-spacing:-.01em}}
.cap-beat{{font-family:"IBM Plex Mono",monospace;font-size:11px;letter-spacing:.08em;text-transform:uppercase;
  color:var(--accent-ink);white-space:nowrap}}
.dials{{font-family:"IBM Plex Mono",monospace;font-size:13px;color:var(--muted);font-variant-numeric:tabular-nums;line-height:1.6}}
.note{{margin-top:26px;color:var(--muted);font-size:14px;max-width:64ch}}
.note b{{color:var(--ink);font-weight:500}}
footer{{margin-top:clamp(40px,7vw,64px);padding-top:18px;border-top:1px solid var(--line);
  font-family:"IBM Plex Mono",monospace;font-size:12px;color:var(--muted);display:flex;flex-wrap:wrap;gap:6px 16px}}
img,video{{max-width:100%}}
@media (max-width:560px){{.grid{{grid-template-columns:1fr}}}}
</style>

<div class="wrap">
  <header>
    <p class="eyebrow">Local · ComfyUI · one 24 GB card</p>
    <h1>LivePortrait</h1>
    <p class="dek">Exact facial performance on the local stack — no LoRA, no re-generation.
      Dial an expression onto a rendered face, or transfer a real performance from a driving
      clip. Every frame below was rendered on the rig and pulled straight from the run.</p>
    <div class="readout">
{stat_html}
    </div>
  </header>

  <section>
    <div class="sec-label"><span class="num">01</span> <b>Retargeting</b> — the Act-One path</div>
    <figure class="stage">
      <video src="{vid}" autoplay muted loop playsinline></video>
      <figcaption>
        <span><b>178</b> frames</span><span><b>30</b> fps</span><span><b>5.9</b> s clip</span>
        <span>rendered in <b>30 s</b></span><span>driving performance → one portrait</span>
      </figcaption>
    </figure>
    <p class="note">A real actor's performance drives the still: the clip supplies the acting,
      the portrait supplies <b>who</b> is acting. Identity holds; the head motion and expression
      are the driver's. This is the open analogue of Runway Act-One.</p>
  </section>

  <section>
    <div class="sec-label"><span class="num">02</span> <b>Expression editor</b> — one face, four dials</div>
    <div class="grid">
{cards}
    </div>
    <p class="note">The same source frame, cropped to the face and dialed four ways in the
      ExpressionEditor. Small values barely register against the ranges (eyebrow spans −10…15) —
      these are scaled to <b>read as restrained micro-expression, not a mask</b>. Each dialed
      still is a start frame for the next shot.</p>
  </section>

  <footer>
    <span>her_studio.png · source face</span><span>ComfyUI-AdvancedLivePortrait</span>
    <span>validated end-to-end on the rig</span>
  </footer>
</div>'''


if __name__ == "__main__":
    main()
