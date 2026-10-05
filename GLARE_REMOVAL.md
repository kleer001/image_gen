# Glare removal — approved method

**Status:** approved by the repository author on 2026-10-05 as the standard
method to remove glare from photos of printed artwork. Use it unless the task
needs something it cannot give (see [Limits](#limits)).

The method removes specular glare, glossy sheen and fine surface scratches from
a photo or phone scan of printed flat-color artwork, such as a card, a print or
a book illustration. It keeps every mark of the art and restores the colors of
the source photo.

For the other methods that were compared, and why they lost, see
[`FLAT_ART_CLEANUP.md`](FLAT_ART_CLEANUP.md).

## How it works

1. **Qwen-Image-Edit-2509 with the Light Restoration V2 LoRA**
   (`scripts/qwen_light_restoration.py`) repaints the image with soft, even
   light. Glare and scratches go away, and pale strokes and small marks stay.
   It also makes the colors lighter and less saturated, and it tints white
   paper cream.
2. **Color match** (`scripts/match_curves.py`) maps the edit back onto the
   colors of the source, in two parts:
   - One tone curve per RGB channel fixes the overall tone and the paper white.
     For each edit value, the curve takes the median source value.
   - The curved image's colors are grouped (k-means in CIELAB), and each group
     gets its own offset to the source. This corrects small fills that the
     curves get wrong, such as a brown name on a card with a large blue body.
     Each pixel blends the offsets of nearby groups, so no seam shows between
     fills.

   Both parts fit only on pixels that are flat in both images and use medians.
   Glare and scratches cover only part of a fill, so they do not pull the fit.

## Requirements

- Production ComfyUI on port 8188 (`imggen`, or `comfyui/.venv/bin/python
  main.py --listen --port 8188` from `comfyui/`).
- Models already used by `workflows/qwen_image_edit_multiangle.json`:
  `Qwen-Image-Edit-2509-Q6_K.gguf`, `qwen_2.5_vl_7b_fp8_scaled.safetensors`
  and `qwen_image_vae.safetensors`.
- The LoRA `models/loras/qwen_edit_2509_light_restoration_v2.safetensors`
  (catalogued in `models.yaml`). To install only this file:

  ```bash
  HF_HUB_DISABLE_XET=1 hf download dx8152/Qwen-Image-Edit-2509-Light_restoration \
    "移除光影V2.safetensors" --local-dir /tmp/lr
  mv "/tmp/lr/移除光影V2.safetensors" models/loras/qwen_edit_2509_light_restoration_v2.safetensors
  ```

- Run both scripts with `comfyui/.venv/bin/python`. That venv has
  scikit-image and scikit-learn, which `match_curves.py` needs.

## Prepare the input

- Crop the photo to the artwork and remove any backdrop around it.
- Make the paper white before step 1. The curves copy the colors of the
  source, so a gray or tinted paper in the source stays gray or tinted in the
  result.
- Any size works. Qwen fits the image to a bucket of about 1 megapixel and
  keeps the aspect ratio (it center-crops a few pixels). `match_curves.py`
  aligns the source the same way.

## Run

One image:

```bash
comfyui/.venv/bin/python scripts/qwen_light_restoration.py card.png card_qwen.png --seed 1406
comfyui/.venv/bin/python scripts/match_curves.py card_qwen.png card.png card_clean.png
```

A folder of images, one GPU job at a time. The loop frees the GPU after each
image and skips images that already have an output, so you can run it again
to redo only the images that failed:

```bash
for f in in/*.png; do
  n=$(basename "$f" .png)
  [ -f "out/${n}_qwen.png" ] || comfyui/.venv/bin/python scripts/qwen_light_restoration.py \
    "$f" "out/${n}_qwen.png" --seed 1406
  curl -s -X POST http://127.0.0.1:8188/free -H 'Content-Type: application/json' \
    -d '{"unload_models": true, "free_memory": true}'
  [ -f "out/${n}_qwen.png" ] && comfyui/.venv/bin/python scripts/match_curves.py \
    "out/${n}_qwen.png" "$f" "out/${n}.png"
done
```

Now and then the text-encode step runs out of GPU memory
(`torch.OutOfMemoryError` in `TextEncodeQwenImageEditPlus`). The ComfyUI log
then shows that the 16 GB diffusion model of the previous image was still
loaded ("Unloaded partially … 11231 MB remains loaded"); the free call did not
always unload it in time. The script exits with an error, ComfyUI unloads all
models, and a second run of that image works.

Step 1 takes about 200 s per image on an RTX 3090, and step 2 takes a few
seconds on the CPU. Qwen-Image-Edit uses most of the 24 GB card, so do not run
another heavy GPU job at the same time.

## Check the result

- `match_curves.py` prints the median color error (ΔE2000) against the source
  on flat areas of the art, for the edit, after the curves and at the end. It
  also prints the error of the worst color group, which shows a small fill
  that is wrong. A ΔE2000 of about 1 is at the edge of what people can see. On
  the validation images the final median is 0.7 to 1.5 and the worst group is
  below 5. Glare that is left in the source photo adds to the error, so 0 is
  not reachable.
- Look at the small features, such as eyes, pupils and thin strokes. The edit
  model repaints the whole image and can change small details.
- Show the source and the result side by side in a browser gallery (see
  [`BROWSER_DISPLAY.md`](BROWSER_DISPLAY.md)).

## Validation

Median ΔE2000 on flat art against the source photo. "Worst group" is the
median of the worst color group.

| Image | Qwen edit (median / worst group) | Curves only | Curves + groups (final) | Visual check |
|---|---|---|---|---|
| Red dragon, strong wing glare | 4.88 / 6.28 | 0.93 / 1.46 | 0.95 / 1.41 | pass |
| Dark purple dragon, cream belly | 4.82 / 6.33 | 1.30 / 2.46 | 1.11 / 1.91 | pass |
| Gray dragon with gray spots, orange spikes | 5.05 / 7.50 | 1.57 / 2.54 | 1.50 / 2.46 | pass |
| Light-blue dragon, brown horns and brown name | 2.04 / 8.23 | 0.74 / 11.55 | 0.73 / 4.95 | pass; with curves only, the brown name and horns turned gray-green |
| Orange dragon, red wing with glare streaks | 3.72 / 6.58 | 1.06 / 3.67 | 1.02 / 2.45 | pass |

All test images are phone photos of glossy printed cards from one deck of
flat-color cartoon dragons on white.

The full deck (18 cards) gave a final median of 0.73 to 1.66 and a worst
group of 1.41 to 4.95. With curves only, three cards had a worst group of 12
to 14, so the group step is needed. Every dragon passed the visual check. Of
18 Qwen runs, 2 ran out of GPU memory and worked on the second run.

## Limits

- The output is about 1 megapixel, not the input size.
- The color match changes color only. It cannot put back a mark that the
  edit model removed, and it cannot remove glare that the edit model left.
- A fill smaller than a few hundred flat pixels gets no group offset of its
  own; it takes the offsets of the groups nearest in color.
- Thin lettering has few flat pixels, so its color is the least reliable. On
  one card a khaki name came out green (ΔE2000 17 on the name). Check
  lettering by eye, or crop it out before you use the result.
- The edit model can redraw small features. Always check faces and fine
  marks.
- For exact input size and perfectly flat fills, with pale marks lost, use
  `scripts/flat_palette.py` instead (see `FLAT_ART_CLEANUP.md`).
