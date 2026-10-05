#!/usr/bin/env python3
"""Match an edited image's colors back to its source: tone curves, then color groups.

Image-edit models (Qwen-Image-Edit, Flux Kontext) often shift color: lighter,
less saturated, or a tinted paper white. This script corrects the edit in two
steps:

1. One monotonic curve per RGB channel maps the edit onto the source. This
   fixes the overall tone and the paper white, but the largest fill sets the
   curves, so a small fill of another hue can come out wrong.
2. The curved image's colors are grouped with k-means in CIELAB. Each group
   gets its own offset: the median CIELAB difference between source and curved
   image over the group's pixels. Each pixel takes a blend of the group offsets,
   weighted by its color distance to each group, so edges between two fills
   blend smoothly and no group boundary shows.

The fit uses only pixels that are flat in both images, so edges and small
misalignment do not count. For each edit value, the target is the median source
value at the same pixels. The median ignores glare and scratches that cover
only part of a fill. Isotonic regression keeps each curve increasing, and its
ends are pinned to 0 and 255 so tones absent from the flat areas (pupils,
paper) stay in range. Groups with too few flat pixels get no offset.

The source is resized to the edit's width and center-cropped to its height. This
is how FluxKontextImageScale fits an image to its bucket, so Kontext and
Qwen-Image-Edit outputs line up with their inputs.

Needs scikit-image and scikit-learn (the production ComfyUI venv has them):

    comfyui/.venv/bin/python scripts/match_curves.py edited.png source.png out.png
"""
import argparse

import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import deltaE_ciede2000, lab2rgb, rgb2lab
from sklearn.cluster import KMeans
from sklearn.isotonic import IsotonicRegression

EDIT_FLAT = 4.0  # max Sobel gradient (levels/px) for a flat pixel in the edit
SOURCE_FLAT = 6.0  # the source is noisier (grain, glare), so allow more
MIN_SAMPLES = 30  # an edit value needs this many flat pixels to give a curve point
GROUPS = 12  # k-means color groups for the second step
MIN_GROUP = 300  # flat pixels a group needs before it gets its own offset
GROUP_SIGMA = 5.0  # CIELAB distance over which the offsets of nearby groups blend
FIT_SAMPLE = 100_000


def align_source(source, size):
    w, h = size
    fit_h = round(source.height * w / source.width)
    top = (fit_h - h) // 2
    return np.asarray(source.resize((w, fit_h), Image.Resampling.LANCZOS))[top:top + h]


def flat_mask(*images):
    mask = np.ones(images[0].shape[:2], bool)
    for img, limit in zip(images, (EDIT_FLAT, SOURCE_FLAT), strict=True):
        a = img.astype(float)
        grad = np.max([np.hypot(ndi.sobel(a[..., c], 0), ndi.sobel(a[..., c], 1)) for c in range(3)], 0) / 8
        mask &= grad < limit
    return ndi.binary_erosion(mask, iterations=2)


def fit_curves(edit, ref, mask):
    lut = np.empty((256, 3))
    for c in range(3):
        e, r = edit[..., c][mask], ref[..., c][mask].astype(float)
        xs, ys, ws = [0], [0.0], [1]
        for v in range(256):
            hit = r[e == v]
            if len(hit) >= MIN_SAMPLES:
                xs.append(v)
                ys.append(float(np.median(hit)))
                ws.append(len(hit))
        xs, ys, ws = xs + [255], ys + [255.0], ws + [1]
        iso = IsotonicRegression(increasing=True, out_of_bounds="clip").fit(xs, ys, sample_weight=ws)
        lut[:, c] = np.interp(np.arange(256), xs, iso.predict(xs))
    return np.clip(lut, 0, 255)


def fit_groups(lab, lab_ref, mask):
    """Return k-means group centers and each group's median CIELAB offset to the source."""
    pixels, target = lab[mask], lab_ref[mask]
    rng = np.random.default_rng(0)
    sample = pixels[rng.choice(len(pixels), min(FIT_SAMPLE, len(pixels)), replace=False)]
    km = KMeans(GROUPS, n_init=4, random_state=0).fit(sample)
    labels = km.predict(pixels)
    offsets = np.zeros((GROUPS, 3))
    for g in range(GROUPS):
        members = labels == g
        if members.sum() >= MIN_GROUP:
            offsets[g] = np.median(target[members] - pixels[members], axis=0)
    return km.cluster_centers_, offsets


def apply_groups(lab, centers, offsets):
    d2 = ((lab[..., None, :] - centers) ** 2).sum(-1)
    weights = np.exp(-(d2 - d2.min(-1, keepdims=True)) / (2 * GROUP_SIGMA**2))
    weights /= weights.sum(-1, keepdims=True)
    return lab + weights @ offsets


def delta_e(a, b, mask):
    return deltaE_ciede2000(rgb2lab(a[mask] / 255.0), rgb2lab(b[mask] / 255.0))


def worst_group(img, ref, mask, centers):
    """Median dE2000 of the worst color group, so a small wrong fill shows in the report."""
    lab = rgb2lab(img[mask] / 255.0)
    labels = ((lab[:, None, :] - centers) ** 2).sum(-1).argmin(1)
    errors = delta_e(img, ref, mask)
    return max(np.median(errors[labels == g]) for g in range(len(centers)) if (labels == g).sum() >= MIN_GROUP)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("edited")
    ap.add_argument("source")
    ap.add_argument("out")
    a = ap.parse_args()
    edit = np.asarray(Image.open(a.edited).convert("RGB"))
    ref = align_source(Image.open(a.source).convert("RGB"), (edit.shape[1], edit.shape[0]))
    mask = flat_mask(edit, ref)
    lut = fit_curves(edit, ref, mask)
    curved = np.stack([lut[edit[..., c], c] for c in range(3)], -1).round().astype(np.uint8)
    lab_curved, lab_ref = rgb2lab(curved / 255.0), rgb2lab(ref / 255.0)
    centers, offsets = fit_groups(lab_curved, lab_ref, mask)
    out = (np.clip(lab2rgb(apply_groups(lab_curved, centers, offsets)), 0, 1) * 255).round().astype(np.uint8)
    Image.fromarray(out).save(a.out)
    art = mask & (ref.min(axis=2) < 215)  # flat pixels that are ink, not paper
    print(f"median dE2000 on flat art: edit {np.median(delta_e(edit, ref, art)):.2f}, "
          f"curves {np.median(delta_e(curved, ref, art)):.2f}, final {np.median(delta_e(out, ref, art)):.2f} | "
          f"worst color group: edit {worst_group(edit, ref, art, centers):.2f}, "
          f"curves {worst_group(curved, ref, art, centers):.2f}, final {worst_group(out, ref, art, centers):.2f} | {a.out}")


if __name__ == "__main__":
    main()
