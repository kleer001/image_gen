# Flat-art cleanup

> The approved method is in [`GLARE_REMOVAL.md`](GLARE_REMOVAL.md): Qwen Light
> Restoration followed by `match_curves.py`. This page records the comparison
> behind it.

How to remove glare (glossy sheen), surface scratches and uneven fills from a
photo of printed flat-color artwork, such as a playing card, clip art or a comic
panel, and keep the anti-aliased edges.

## First choice: get a better source

A cleanup only guesses at the art. A clean source does not guess.

- **Find the original.** Commercial card art is often a licensed stock
  illustration. Crop the art without its text and use a reverse image search.
  Yandex Images ("search by image") is the strongest engine for illustration;
  it found a stock source where a text search on the printed names found
  nothing. A stock vector set gives exact flat fills at any size.
- **Re-shoot without glare.** Put polarizer film on the light and a polarizing
  filter on the lens, then turn the lens filter until the sheen goes away
  (cross-polarization). This removes sheen, but not scratches. As an
  alternative, take several shots with the light at different angles, align
  them, and keep the darkest value per pixel.

## Methods on this stack

The results below come from one test: a phone photo of a glossy printed card
with a flat-color cartoon dragon on white. The times are for an RTX 3090.

| Method | Glare | Scratches | Pale marks in a fill | Color | Edges | Output size | Time |
|---|---|---|---|---|---|---|---|
| `scripts/flat_palette.py` | removed | removed, except a few small dashes | lost (they merge into the fill) | close to the source | anti-aliasing kept; thin dark outlines lost | same as input | about 20 s, CPU |
| Flux Kontext (`scripts/kontext_edit.py`) | mostly removed; slight mottle on dark fills | removed | kept | closest to the source | kept | about 1 MP (880×1184 for portrait) | about 105 s at 30 steps |
| `scripts/qwen_light_restoration.py` | removed | removed | kept | lighter and less saturated; white paper turns cream with a vignette | soft | about 1 MP | about 200 s at 20 steps |
| Qwen, then `scripts/match_curves.py` | removed | removed | kept | close to the source (median ΔE2000 on the art 0.95, against 4.9 before the color match); paper white again | soft | about 1 MP | plus about 5 s, CPU |

Choose by what matters most:
- For the cleanest result at about 1 MP, use Qwen Light Restoration followed by
  `match_curves.py`. It removes glare and scratches, keeps every mark, and the
  color match restores the source colors.
- For exact size and perfectly flat fills, use `flat_palette.py`.
- Kontext keeps marks and colors with no curve step, but leaves some mottle.

## Commands

The palette method needs opencv-contrib (`cv2.ximgproc`), scikit-image and
scikit-learn. The production ComfyUI venv has them:

```bash
comfyui/.venv/bin/python scripts/flat_palette.py in.png out.png --lambda 0.001 --k 16 --merge-de 6
```

The Kontext and Qwen methods need production ComfyUI on port 8188:

```bash
comfyui/.venv/bin/python scripts/kontext_edit.py \
  "Remove the glare, glossy reflections and scratches from this photo of a printed card. Keep the illustration, colors, outlines and text exactly the same, with flat even colors." \
  --ref in.png --steps 30 --guidance 2.5 --no-open
comfyui/.venv/bin/python scripts/qwen_light_restoration.py in.png qwen.png --seed 1
comfyui/.venv/bin/python scripts/match_curves.py qwen.png in.png out.png
```

`match_curves.py` fits one increasing tone curve per RGB channel from the edit
to its source, then corrects each color group (k-means in CIELAB) with its own
offset, so a small fill of another hue is not pulled off by the largest fill.
It uses only pixels that are flat in both images, and medians, so glare and
scratches in the source do not pull the fit. The source is resized to the
edit's width and center-cropped, which is how the edit models fit an image to
their size bucket. The color match changes color only; it does not move glare
or marks. Details and validation are in [`GLARE_REMOVAL.md`](GLARE_REMOVAL.md).

Qwen-Image-Edit (Q6_K GGUF plus a 7B text encoder) and Flux Kontext are both
large. Run one job at a time, and release memory between jobs:

```bash
curl -X POST http://127.0.0.1:8188/free -H 'Content-Type: application/json' \
  -d '{"unload_models": true, "free_memory": true}'
```

## How `flat_palette.py` works and how to tune it

1. L0 gradient minimization (Xu et al., "Image Smoothing via L0 Gradient
   Minimization", SIGGRAPH Asia 2011) flattens low-contrast variation inside
   each fill and keeps strong edges.
2. K-means in CIELAB picks a palette. Clusters closer than `--merge-de` are
   treated as glare variants of one fill. They merge into the darker cluster,
   because glare only lightens.
3. A pixel well inside a fill takes its palette color. Each edge pixel becomes
   a blend of its two nearest fill colors in linear light. The script takes the
   blend weight from the original pixel, so the source edge profile stays.

| Setting | Effect when too high | Effect when too low |
|---|---|---|
| `--lambda` | erases thin lines, eyebrows and dots (0.01 erases wing veins) | keeps glare texture in the fill |
| `--merge-de` | merges two real colors that are close | leaves glare as a hard-edged patch of a second color |

Known limits:
- Marks whose color is close to their fill (pale highlight strokes, light
  swirls) merge into the fill at every tested setting.
- A thin dark outline around shapes, one or two pixels wide, becomes part of
  the edge blend and disappears.
- The lightest palette entry becomes pure white, so make the paper white first.

## Methods not recommended

- **Classical specular-highlight removal.** These methods use the dichromatic
  reflection model (Tan and Ikeuchi 2005, and later work). They assume colored
  surfaces, so they fail on white and gray, and they target small highlights,
  not a broad sheen.
- **Document deshadow and deglare networks** (DocShadow, DocRes, TSHRNet).
  They are trained on text pages or natural photos, and no source shows results
  on illustration. They were not tested on this stack.
