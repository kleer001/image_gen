#!/usr/bin/env python3
"""Flatten flat-color artwork to a palette while keeping anti-aliased edges.

For photos or scans of flat-color illustration (cartoon cards, clip art, comics)
where glare, sheen, print grain or scratches make the fills uneven. Three steps:

1. L0 gradient minimization (Xu et al. 2011, cv2.ximgproc.l0Smooth) flattens
   low-contrast variation inside each fill and keeps strong edges.
2. K-means in CIELAB picks a palette from the smoothed image. Clusters closer
   than --merge-de are glare variants of one fill and merge into the darker one,
   because glare only lightens.
3. Pixels well inside a fill take their palette color. Each edge pixel is
   rebuilt as a blend of its two nearest fill colors in linear light, with the
   blend weight projected from the ORIGINAL pixel, so the edge profile
   (anti-aliasing) of the source survives.

Trade-off: marks whose color is close to their fill (pale highlight strokes,
light swirls) merge into the fill. Lower --lambda and --merge-de keep more of
them and also keep more glare. See FLAT_ART_CLEANUP.md.

Needs opencv-contrib (ximgproc), scikit-image and scikit-learn, which the
production ComfyUI venv has:

    comfyui/.venv/bin/python scripts/flat_palette.py in.png out.png [--lambda 0.001] [--k 16] [--merge-de 6]
"""
import argparse

import cv2
import numpy as np
from PIL import Image
from scipy import ndimage as ndi
from skimage.color import lab2rgb, rgb2lab
from sklearn.cluster import KMeans

CORE_RADIUS = 2  # a pixel is inside a fill when its whole 5x5 window has one label
MIN_ISLAND = 40  # label islands smaller than this (px) are scratch fragments
SAMPLE = 200_000


def to_linear(srgb):
    s = srgb / 255.0
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def to_srgb(linear):
    v = np.clip(linear, 0, 1)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055) * 255


def pick_palette(smooth, k, merge_de):
    lab = rgb2lab(smooth / 255.0).reshape(-1, 3)
    rng = np.random.default_rng(0)
    sample = lab[rng.choice(len(lab), min(SAMPLE, len(lab)), replace=False)]
    km = KMeans(k, n_init=4, random_state=0).fit(sample)
    counts = np.bincount(km.labels_, minlength=k)
    kept = []
    for i in np.argsort(km.cluster_centers_[:, 0]):  # darkest first
        c = km.cluster_centers_[i]
        if counts[i] >= 50 and all(np.linalg.norm(c - km.cluster_centers_[j]) > merge_de for j in kept):
            kept.append(i)
    return km.cluster_centers_[kept]


def despeckle(labels):
    """Give each small label island the label of the nearest pixel outside it."""
    small = np.zeros(labels.shape, bool)
    for value in np.unique(labels):
        comp, _ = ndi.label(labels == value)
        areas = np.bincount(comp.ravel())
        small |= (comp > 0) & (areas[comp] < MIN_ISLAND)
    _, (iy, ix) = ndi.distance_transform_edt(small, return_indices=True)
    return labels[iy, ix]


def flatten(rgb, l0_lambda, k, merge_de):
    smooth = cv2.ximgproc.l0Smooth(rgb, None, l0_lambda, 2.0)
    pal_lab = pick_palette(smooth, k, merge_de)
    pal_srgb = lab2rgb(pal_lab[None]).reshape(-1, 3) * 255
    pal_srgb[np.argmax(pal_lab[:, 0])] = 255  # the lightest entry is the paper white
    pal_lin = to_linear(pal_srgb)

    dist_lab = np.linalg.norm(rgb2lab(smooth / 255.0)[..., None, :] - pal_lab, axis=-1)
    labels = despeckle(dist_lab.argmin(-1))

    window = 2 * CORE_RADIUS + 1
    core = np.zeros(labels.shape, bool)
    dist_core = np.empty((len(pal_lab),) + labels.shape, np.float32)
    for value in range(len(pal_lab)):
        inside = ndi.uniform_filter((labels == value).astype(np.float32), window) > 0.999
        core |= inside
        dist_core[value] = ndi.distance_transform_edt(~inside) if inside.any() else np.inf

    out = pal_lin[labels]
    ey, ex = np.nonzero(~core)
    nearest = np.argsort(dist_core[:, ey, ex], axis=0)[:3].T
    src = to_linear(rgb.astype(np.float64))[ey, ex]
    best_err = np.full(len(ey), np.inf)
    best = np.zeros_like(src)
    for a, b in ((0, 1), (0, 2), (1, 2)):
        ci, cj = pal_lin[nearest[:, a]], pal_lin[nearest[:, b]]
        span = ci - cj
        alpha = ((src - cj) * span).sum(1) / np.maximum((span**2).sum(1), 1e-9)
        blend = np.clip(alpha, 0, 1)[:, None] * span + cj
        err = ((src - blend) ** 2).sum(1)
        better = err < best_err
        best_err[better], best[better] = err[better], blend[better]
    out[ey, ex] = best
    return to_srgb(out).round().astype(np.uint8), pal_srgb


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("--lambda", dest="l0_lambda", type=float, default=0.001,
                    help="L0 smoothing strength; higher erases more glare and more detail")
    ap.add_argument("--k", type=int, default=16, help="k-means clusters before merging")
    ap.add_argument("--merge-de", type=float, default=6.0,
                    help="CIELAB distance under which two clusters count as one fill")
    a = ap.parse_args()
    rgb = np.asarray(Image.open(a.src).convert("RGB"))
    out, palette = flatten(rgb, a.l0_lambda, a.k, a.merge_de)
    Image.fromarray(out).save(a.dst)
    print(f"{len(palette)} colors -> {a.dst}")


if __name__ == "__main__":
    main()
